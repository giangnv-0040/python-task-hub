"""Nghiep vu comment: tao comment + bao assignee qua Celery trong 1 cho (R13)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import comment as crud_comment
from app.models.comment import Comment
from app.schemas.comment import CommentCreate
from app.services import notification as notification_service


async def create_comment(
    db: AsyncSession, task_id: int, data: CommentCreate, author_id: int
) -> Comment:
    comment = await crud_comment.create_comment(db, task_id, data, author_id=author_id)
    await notification_service.notify_comment_created(comment)
    return comment
