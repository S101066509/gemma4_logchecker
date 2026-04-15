from pydantic import BaseModel, Field
from typing import List
from app.core.config import settings

class DiagnosticReport(BaseModel):
    """
    診斷報告格式
    """
    severity: str = Field(..., description="錯誤嚴重程度 (Low, Medium, High, Critical)")
    root_cause: str = Field(..., description="導致錯誤的根本原因分析")
    suggested_fix: str = Field(..., description="具體的修復建議或代碼修改方向")
    related_files: List[str] = Field(default=[], description="日誌中提到的相關檔案路徑或代碼位置")
    confidence: float = Field(..., description="對此診斷的信心指標 (0.0 to 1.0)")

class LogAnalysisInput(BaseModel):
    """
    使用者傳入的日誌分析請求格式
    """
    log_text: str = Field(
        ...,
        max_length=settings.max_text_length,
        description="純文字日誌內容"
    )
    image_base64: str = Field(
        default="",
        max_length=settings.max_image_base64_length,
        description="可選：上傳的報錯截圖 (Base64，請勿包含 data:image/... 前綴)"
    )
