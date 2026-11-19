from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from langserve import add_routes
from langchain_core.runnables import RunnableLambda
from contextlib import asynccontextmanager
import uvicorn
import logging
import time
import uuid
from collections import deque
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from app.schemas import LogAnalysisInput, DiagnosticReport
from app.logic.log_parser import clean_log_text, extract_critical_sections
from app.chain import analyze_log_with_gemma
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 啟動時驗證安全設定 ---
    if settings.api_key == "your-secret-api-key-12345":
        raise RuntimeError(
            "API_KEY 仍為預設值。請設定環境變數 API_KEY 後再啟動。"
        )
    yield
    # 可在此加入關閉時的清理邏輯

app = FastAPI(
    title="Gemma 4 日誌診斷伺服器",
    version="1.0",
    description="利用 Gemma 4 E4B 執行自動日誌掃描、脫敏與多模態根因分析",
    lifespan=lifespan,
)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("gemma4-logchecker")

# 簡單的 in-memory 速率限制 (每個 IP 每分鐘)
_rate_limit_store = {}
_rate_limit_window_sec = 60

# 解決 CORS 跨網域問題
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_guard_and_logging(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # Request size limit (HTTP 層)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_body_bytes:
        logger.warning(
            "request_id=%s method=%s path=%s status=%s reason=body_too_large",
            request_id,
            request.method,
            request.url.path,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
        return Response(
            content="Request body too large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            headers={"X-Request-ID": request_id}
        )
    if not content_length:
        body = await request.body()
        if len(body) > settings.max_body_bytes:
            logger.warning(
                "request_id=%s method=%s path=%s status=%s reason=body_too_large",
                request_id,
                request.method,
                request.url.path,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
            return Response(
                content="Request body too large",
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                headers={"X-Request-ID": request_id}
            )
        request._body = body

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    q: deque = _rate_limit_store.get(client_ip)
    if q is None:
        q = deque()
        _rate_limit_store[client_ip] = q
    # 清除過期
    while q and now - q[0] > _rate_limit_window_sec:
        q.popleft()
    if len(q) >= settings.rate_limit_per_minute:
        logger.warning(
            "request_id=%s method=%s path=%s status=%s reason=rate_limited client_ip=%s",
            request_id,
            request.method,
            request.url.path,
            status.HTTP_429_TOO_MANY_REQUESTS,
            client_ip,
        )
        return Response(
            content="Too Many Requests",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"X-Request-ID": request_id}
        )
    q.append(now)

    # Proceed
    api_key = request.headers.get("X-API-Key")
    api_key_tail = f"...{api_key[-4:]}" if api_key and len(api_key) >= 4 else "none"
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s client_ip=%s api_key=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        client_ip,
        api_key_tail,
    )
    return response

# --- API 金鑰認證機制 ---
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 API Key",
        )
    return api_key

# 啟動驗證邏輯已移至 lifespan context manager

@app.post(
    "/diagnose",
    response_model=DiagnosticReport,
    summary="分析日誌並輸出結構化診斷報告",
    description=(
        "接收日誌文字與可選截圖，先做脫敏與關鍵片段提取，"
        "再呼叫 Gemma 4 輸出 DiagnosticReport。"
    ),
    responses={
        200: {"description": "成功產生診斷報告"},
        401: {"description": "X-API-Key 無效或缺失"},
        413: {"description": "請求內容超過大小限制"},
        429: {"description": "請求過於頻繁，觸發速率限制"},
        500: {"description": "伺服器內部錯誤"},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "text_only_log": {
                            "summary": "純文字日誌",
                            "description": "僅提供日誌文字，不含截圖。",
                            "value": {
                                "log_text": "ERROR 2026-04-15 10:12:31 database connection refused at db.py:42",
                                "image_base64": "",
                            },
                        },
                        "text_and_image": {
                            "summary": "日誌 + 截圖",
                            "description": "同時提供日誌與 Base64 截圖（不含 data:image 前綴）。",
                            "value": {
                                "log_text": "CRITICAL: NullReferenceException at service startup",
                                "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                            },
                        },
                    }
                }
            }
        }
    },
)
def diagnose_log(input_data: LogAnalysisInput, _: str = Depends(verify_api_key)):
    """
    自定義 API 路由：結合預處理與 AI 診斷
    """
    try:
        # 1. 預處理：清洗與提取關鍵片段
        cleaned_text = clean_log_text(input_data.log_text)
        critical_text = extract_critical_sections(cleaned_text)
        
        # 2. 呼叫 Gemma 4 進行分析
        report = analyze_log_with_gemma(
            log_text=critical_text, 
            image_base64=input_data.image_base64
        )
        
        return report
        
    except Exception:
        logger.exception("診斷流程發生未預期錯誤")
        raise HTTPException(
            status_code=500,
            detail="伺服器內部錯誤，請稍後再試。",
        )


# 同時註冊 LangServe 標準路由 (方便 Playground 測試單一 Chain)
# 注意：這裡透過 .with_types() 明確宣告輸入/輸出，修復 Playground 的 UI 渲染問題
if settings.enable_playground:
    playground_dependencies = [] if settings.allow_playground_without_api_key else [Depends(verify_api_key)]

    add_routes(
        app,
        RunnableLambda(lambda x: analyze_log_with_gemma(**x)).with_types(
            input_type=LogAnalysisInput,
            output_type=DiagnosticReport
        ),
        path="/analyze_raw",
        dependencies=playground_dependencies,
    )


def custom_openapi():
    """
    隱藏 LangServe 內部路由於 Swagger 文件，保留對外主要 API。
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["paths"] = {
        path: item
        for path, item in schema.get("paths", {}).items()
        if not path.startswith("/analyze_raw")
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == "__main__":
    print(f"Gemma 4 日誌診斷系統已啟動：http://localhost:{settings.app_port}")
    print(f" 使用自定義 API：POST /diagnose")
    print(f" 使用測試介面：http://localhost:{settings.app_port}/analyze_raw/playground")
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
