from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class UploadRequest(BaseModel):
    filename: str
    content_type: str

class UploadResponse(BaseModel):
    upload_url: str
    file_key: str
    expires_in: int

class UploadConfirmation(BaseModel):
    file_key: str
    disabled_modules: List[str] = []
 
class VideoRecord(BaseModel):
    video_id: str
    user_id: str
    file_key: str
    filename: str
    status: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None