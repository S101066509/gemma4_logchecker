import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    系統全局設定
    """
    # Ollama 推論引擎 URL (本地開發預設為 localhost)
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # 使用的模型名稱 (Gemma 4 E4B)
    model_name: str = os.getenv("MODEL_NAME", "gemma4:e4b")
    
    # 應用程式啟動埠號 與 記錄等級
    app_port: int = int(os.getenv("APP_PORT", 8080))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # 外部服務存取授權用的 API Key
    api_key: str = os.getenv("API_KEY", "your-secret-api-key-12345")

    # 是否允許 Playground 免 API Key（僅建議開發環境）
    # 預設為 False，部署者需透過環境變數明確開啟
    allow_playground_without_api_key: bool = (
        os.getenv("ALLOW_PLAYGROUND_WITHOUT_API_KEY", "False").lower() == "true"
    )

    # 是否啟用 Playground（正式環境建議關閉）
    enable_playground: bool = (
        os.getenv("ENABLE_PLAYGROUND", "False").lower() == "true"
    )

    # 請求限制
    max_body_bytes: int = int(os.getenv("MAX_BODY_BYTES", 6_000_000))
    max_text_length: int = int(os.getenv("MAX_TEXT_LENGTH", 200_000))
    # 2MB 圖片 base64 約 2.7MB（含少量緩衝）
    max_image_base64_length: int = int(os.getenv("MAX_IMAGE_BASE64_LENGTH", 2_800_000))

    # 速率限制 (每分鐘每個 IP)
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))

    # LLM 重試次數
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", 2))

settings = Settings()
