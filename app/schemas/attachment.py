from datetime import datetime

from app.schemas.base import BaseSchema


class AttachmentRead(BaseSchema):
    # Khong expose storage_key: la chi tiet noi bo cua storage backend
    id: int
    task_id: int
    uploaded_by: int
    filename: str
    content_type: str
    size: int
    created_at: datetime
