from datetime import datetime

from pydantic import Field

from app.core.constants import COMMENT_CONTENT_MAX_LENGTH, MIN_LENGTH_DEFAULT
from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    # author_id lay tu current_user o router, khong nhan tu body (R20)
    content: str = Field(
        min_length=MIN_LENGTH_DEFAULT, max_length=COMMENT_CONTENT_MAX_LENGTH
    )


class CommentRead(BaseSchema):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
