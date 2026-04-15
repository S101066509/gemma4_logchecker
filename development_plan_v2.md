# 🚀 AI 多模態日誌診斷系統：Gemma 4 開發規劃書

本文件定義了系統的第一階段 (MVP) 實作路徑。本版本專門針對 **Google Gemma 4 E4B** 模型進行優化，利用其快速的推論能力與原生多模態支援，並結合 **Ollama (宿主機) + Docker (服務)** 的架構。

---

## 🛠️ 1. 使用技術 (Technical Stack)

| 元件 | 關鍵技術 | 說明 |
| :--- | :--- | :--- |
| **開發首選模型** | **Gemma 4 E4B** | **高效能首選**：8B 總參數，具備 128k 長上下文，適合快速開發與即時掃描。 |
| **進階備選模型** | **Gemma 4 26B A4B** | **智力首選 (MoE)**：用於複雜連鎖錯誤分析，具備 256k 上下文。 |
| **推論引擎 (Host)** | **Ollama (Native)** | 確保 Mac M4 Pro 呼叫 Metal 加速，驅動 Gemma 4。 |
| **服務容器 (Docker)** | **LangChain + LangServe** | 負責邏輯鏈 (LCEL) 編排，支援多模態資料傳輸。 |
| **向量資料庫 (Docker)** | **移除** | **已移除**：目前不包含 RAG 相關內容。 |

---

## 📂 2. 目錄結構 (Directory Structure)

```text
log-ai-analyzer/
├── app/                                 # 核心代碼 (Service Container)
│   ├── server.py                        # 入口：註冊 LangServe 路由
│   ├── chain.py                         # 邏輯：定義 Gemma 4 專屬處理鏈 (含 Thinking 支援)
│   ├── logic/                           # 業務模組
│   │   └── log_parser.py                # 🔑 關鍵：日誌脫敏與多模態資料打包
│   ├── core/
│   │   ├── config.py                    # 配置：Ollama URL 與長上下文參數 (num_ctx: 131072)
│   │   └── constants.py                 # 常數：Gemma 4 專用 Prompt 範本
│   └── schemas.py                       # 定義：Pydantic 結構化診斷報告
├── deploy/                              # 部署配置
│   ├── Dockerfile                       # 極輕量 Python 環境
│   ├── docker-compose.yml               # 雙容器編排 (Service + DB)
│   └── .env                             # 環境變數 (如 OLLAMA_HOST)
```

---

## 🧠 3. Gemma 4 E4B 的開發細節

### A. 關鍵優勢應用
*   **128k 上下文**：利用 E4B 的長文本能力，我們在 `log_parser.py` 中可以放入更長、更完整的上下文 (Context)，降低模型因為片段訊息導致誤判的機率。
*   **快速迭代**：E4B 在 M4 Pro 上具備極高的 throughput，讓 Playground 測試如同即時對話般流暢。

### B. 多模態圖文對齊
*   使用者可以同時上傳純文字日誌與螢幕截圖。Gemma 4 會透過視覺輔助釐清發生錯誤時的 UI 狀態。

---

## 🗺️ 4. 開發階段 (Roadmap)

### 第一階段：基礎設施建立 (Today)
* [ ] 初始化目錄結構與空檔案。
* [ ] 完成 `docker-compose.yml` 網路配置。
* [ ] 確認本地 `ollama pull gemma4:e4b` 成功。

### 第二階段：推論鏈開發 (Day 2)
* [ ] 實作 `chain.py` 使用 `ChatOllama` 連結 E4B。
* [ ] 實作 `log_parser.py` 將截圖 Base64 與日誌文字打包為單一 Prompt。

### 第三階段：介面與穩定化 (Day 3)
* [ ] 啟動 LangServe 並在網頁介面測試。
* [ ] 提供結構化 JSON 輸出診斷報表。
