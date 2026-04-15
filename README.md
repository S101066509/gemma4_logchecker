# Gemma 4 日誌診斷系統 (Log Checker)

這是一個利用 Google Gemma 4 (E4B) 與 LangChain 打造的自動化伺服器日誌分析系統。系統具備日誌內容清洗、脫敏處理前作業，並能產生高度結構化的 JSON 根因分析報告與修復建議。

## 使用技術

- Python 3.11
- FastAPI + Uvicorn
- LangChain / LangServe
- Ollama（Gemma 4）
- Pydantic / pydantic-settings
- Pytest（單元測試）
- Docker / Docker Compose

## 如何啟動伺服器

設定請參考 `.env.example`（可先複製為 `.env` 後再依環境調整）。

建議優先使用 Docker Compose 啟動（預設 `0.0.0.0:8080`）：

```bash
docker compose -f deploy/docker-compose.yml up --build
```

若要在本機 Python 環境直接啟動，請在專案根目錄執行：

```bash
python -m app.server
```

### 必要環境變數
請先設定 `API_KEY`，避免服務以預設金鑰啟動。

`OLLAMA_BASE_URL` 需依執行方式設定：
```bash
# 本機直接執行 python -m app.server
OLLAMA_BASE_URL=http://localhost:11434

# 使用 Docker Compose 執行服務（容器內連宿主機 Ollama）
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

若要啟用 Playground（僅限開發環境），請設定：
```
ENABLE_PLAYGROUND=true
```

若要允許 Playground 免 API Key（僅限開發環境），請設定：
```
ALLOW_PLAYGROUND_WITHOUT_API_KEY=true
```

部署範例可參考 `.env.example`。

可先用以下指令檢查 Ollama 連線是否正常：
```bash
curl http://localhost:11434/api/tags
```

---

## API 介接文件

系統提供以下主要端點 (Endpoints) 供外部應用程式與開發人員使用。

### 1. 核心診斷 API
這支 API 會自動對傳入的日誌進行預處理（過濾掉無雜訊），然後送交 AI 模型進行結構化診斷。

* **Endpoint**: `POST /diagnose`
* **Content-Type**: `application/json`
* **Authorization**: 必須在 Header 帶上 `X-API-Key`。（請使用你在 `.env` 設定的 `API_KEY` 值）

#### Request (請求格式)
```json
{
  "log_text": "錯誤的日誌或 Exception Traceback (字串，必填)",
  "image_base64": "錯誤截圖 Base64（請勿包含 data:image/... 前綴，選填）"
}
```

#### Response (成功回傳)
回傳結果是一個經過 Pydantic 嚴格驗證的 JSON 物件。
```json
{
  "severity": "High",
  "root_cause": "導致錯誤的根本原因分析 (中文描述)。",
  "suggested_fix": "具體的修復建議或代碼修改方向 (中文描述)。",
  "related_files": [
    "預估出現錯誤的檔案名稱"
  ],
  "confidence": 0.95
}
```

`confidence` 為模型信心分數（0.0~1.0）。系統會對低證據輸入（例如僅短文字、缺少明確錯誤訊號、無 related_files）自動做保守校正，避免過高信心。

#### 呼叫範例 (cURL)
```bash
curl -X POST "http://localhost:8080/diagnose" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <YOUR_API_KEY>" \
     -d '{
           "log_text": "TypeError: null is not an object (evaluating '\''state.app.version'\'')",
           "image_base64": ""
         }'
```

#### 呼叫範例 (JavaScript Fetch)
```javascript
const analyzeLog = async () => {
  const response = await fetch("http://localhost:8080/diagnose", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-API-Key": "<YOUR_API_KEY>"
    },
    body: JSON.stringify({
      log_text: "NullPointerException at line 42",
      image_base64: "" 
    })
  });
  const result = await response.json();
  console.log("診斷結果：", result);
};
```

---

### 2. 開發者視覺化測試介面 (Playground)
系統內建了 LangServe 提供的圖形化操作介面，供開發者快速調試 AI 分析能力。此介面直接調用底層的分析鏈 (Chain)，跳過前置的日誌清洗，適合用於測試純 AI 的能力。

* **URL**: `http://localhost:8080/analyze_raw/playground/`
* **使用方式**: 開啟瀏覽器進入該網址，於畫面中可直接輸入 `log_text`，點擊右下方 **Start** 即可看到逐段梳理的生成過程與最終 JSON。
* **啟用條件**: 需設定 `ENABLE_PLAYGROUND=true` 才會啟用。
* **權限說明**: 預設不允許 Playground 免 API Key（可透過 `ALLOW_PLAYGROUND_WITHOUT_API_KEY=true` 開啟）。

---

### 3. API 預設說明文件 (Swagger UI)
基於 FastAPI 自動生成的互動式 API 文件。

* **Swagger UI Docs**: `http://localhost:8080/docs`
* **ReDoc**: `http://localhost:8080/redoc`

---
## 測試（指令）

在專案根目錄執行：

```bash
# 執行全部測試
pytest -q

# 只跑 chain 測試檔
pytest tests/test_chain.py -q

# 只跑單一測試函式
pytest tests/test_chain.py::test_calibrate_confidence_low_evidence_caps_at_0_70 -q
```

---

## 安全與限制
- 具備簡單的 **Rate Limit**（每分鐘每 IP），可透過 `RATE_LIMIT_PER_MINUTE` 調整。
- 有 **HTTP 層請求大小限制**，可透過 `MAX_BODY_BYTES` 調整。
- 輸入長度限制：`MAX_TEXT_LENGTH`、`MAX_IMAGE_BASE64_LENGTH`。
- 內建基本 **Prompt Injection 防護** 與 **敏感資料遮罩**（仍建議在上游做更嚴格的清洗）。
