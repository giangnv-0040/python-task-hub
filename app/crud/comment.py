from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.schemas.comment import CommentCreate


async def get_comment(db: AsyncSession, comment_id: int) -> Comment | None:
    return await db.get(Comment, comment_id)


async def get_task_comment(
    db: AsyncSession, task_id: int, comment_id: int
) -> Comment | None:
    # Loc ca task_id: comment_id cua task khac duoc coi nhu khong ton tai
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.task_id == task_id)
    )
    return result.scalar_one_or_none()


async def create_comment(
    db: AsyncSession, task_id: int, data: CommentCreate, author_id: int
) -> Comment:
    comment = Comment(task_id=task_id, author_id=author_id, **data.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    await db.delete(comment)
    await db.commit()
