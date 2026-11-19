from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from app.core.config import settings
from app.core.constants import SYSTEM_PROMPT, DIAGNOSIS_TEMPLATE
from app.schemas import DiagnosticReport
import logging
import base64
from typing import Any, Optional

# 初始化 Gemma 4 推論引擎 (Ollama)
llm = ChatOllama(
    model=settings.model_name,
    base_url=settings.ollama_base_url,
    num_ctx=131072, # 128k 上下文 
    temperature=0.1 #用於生成精確回答
).with_structured_output(DiagnosticReport)

logger = logging.getLogger("gemma4-logchecker")

def _normalize_image_base64(image_base64: Optional[str]) -> str:
    """將輸入圖片轉為 Ollama 可接受的純 base64 字串，失敗則回傳空字串。"""
    if not image_base64:
        return ""

    cleaned = image_base64.strip()
    if cleaned.startswith("data:"):
        try:
            _, payload = cleaned.split("base64,", 1)
            cleaned = payload.strip()
        except ValueError:
            return ""

    cleaned = "".join(cleaned.split())
    if not cleaned:
        return ""

    try:
        base64.b64decode(cleaned, validate=True)
    except Exception:
        logger.warning("image_base64 格式無效，將略過圖片")
        return ""
    return cleaned


def _build_messages(log_text: str, image_base64: Optional[str]) -> list[SystemMessage | HumanMessage]:
    """建立聊天訊息內容（system + user 多模態輸入）。"""
    user_content: list[dict[str, str]] = [
        {"type": "text", "text": DIAGNOSIS_TEMPLATE.format(log_text=log_text)}
    ]

    normalized_image = _normalize_image_base64(image_base64)
    if normalized_image:
        user_content.append(
            {
                "type": "image_url",
                "image_url": normalized_image,
            }
        )

    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]


def _build_chain(log_text: str, image_base64: Optional[str]) -> RunnableSerializable[Any, DiagnosticReport]:
    """以 LCEL 建立可直接 invoke 的分析鏈。"""
    prompt = ChatPromptTemplate.from_messages(_build_messages(log_text, image_base64))
    return prompt | llm


def _fallback_report() -> DiagnosticReport:
    return DiagnosticReport(
        severity="Medium",
        root_cause="模型輸出格式不完整或解析失敗，無法產生可信診斷。",
        suggested_fix="請確認日誌內容與格式，必要時縮短輸入後重試。",
        related_files=[],
        confidence=0.1,
    )


def _calibrate_confidence(
    report: DiagnosticReport,
    log_text: str,
    has_image: bool,
) -> DiagnosticReport:
    """
    依輸入證據強度保守校正 confidence，避免在證據不足時給過高分數。
    """
    confidence = max(0.0, min(1.0, report.confidence))
    upper_bound = 1.0
    text_upper = log_text.upper()

    has_error_signal = any(
        token in text_upper for token in ("ERROR", "EXCEPTION", "TRACEBACK", "CRITICAL", "FATAL")
    )

    # 證據不足：短輸入且沒有明確錯誤訊號。
    if len(log_text.strip()) < 120 and not has_error_signal:
        upper_bound = min(upper_bound, 0.70)

    # 無法定位實際來源（文件/模組）時，保守限制。
    if not report.related_files:
        upper_bound = min(upper_bound, 0.85)

    # 只有文本、沒有圖片輔助且缺少錯誤訊號，進一步降低上限。
    if not has_image and not has_error_signal:
        upper_bound = min(upper_bound, 0.75)

    report.confidence = min(confidence, upper_bound)
    return report


def analyze_log_with_gemma(log_text: str, image_base64: str = "") -> DiagnosticReport:
    """處理日誌分析：組多模態輸入、呼叫 LLM、失敗時重試並回傳 fallback。"""
    normalized_image = _normalize_image_base64(image_base64)
    chain = _build_chain(log_text, normalized_image)
    has_image = bool(normalized_image)

    for attempt in range(settings.llm_max_retries + 1):
        try:
            report = chain.invoke({})
            return _calibrate_confidence(report, log_text=log_text, has_image=has_image)
        except Exception:
            if attempt >= settings.llm_max_retries:
                logger.exception("LLM 結構化輸出失敗，使用 fallback 回應")
                return _fallback_report()
            logger.warning("LLM 輸出解析失敗，準備重試（attempt=%s）", attempt + 1)
