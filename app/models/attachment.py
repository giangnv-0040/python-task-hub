from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.constants import (
    ATTACHMENT_CONTENT_TYPE_MAX_LENGTH,
    ATTACHMENT_FILENAME_MAX_LENGTH,
    ATTACHMENT_STORAGE_KEY_MAX_LENGTH,
)
from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"
    # Composite index phuc vu GET /tasks/{id}/attachments (WHERE task_id=? ORDER BY id):
    # gop luon truong hop chi loc theo task_id (leftmost prefix), khong can index rieng
    __table_args__ = (Index("ix_attachments_task_id_id", "task_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # ondelete=CASCADE chi xoa row o DB; file tren storage khong tu xoa theo
    # (xoa attachment qua API thi co xoa file, xem services/attachment.py)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Ten file goc chi de hien thi / Content-Disposition, khong dung lam path
    filename: Mapped[str] = mapped_column(String(ATTACHMENT_FILENAME_MAX_LENGTH))
    storage_key: Mapped[str] = mapped_column(
        String(ATTACHMENT_STORAGE_KEY_MAX_LENGTH), unique=True
    )
    content_type: Mapped[str] = mapped_column(String(ATTACHMENT_CONTENT_TYPE_MAX_LENGTH))
    size: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
