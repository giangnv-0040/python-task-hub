from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.associations import bookmarks


async def is_bookmarked(db: AsyncSession, user_id: int, task_id: int) -> bool:
    result = await db.execute(
        select(bookmarks).where(
            bookmarks.c.user_id == user_id, bookmarks.c.task_id == task_id
        )
    )
    return result.first() is not None


async def create_bookmark(db: AsyncSession, user_id: int, task_id: int) -> None:
    await db.execute(insert(bookmarks).values(user_id=user_id, task_id=task_id))
    await db.commit()
