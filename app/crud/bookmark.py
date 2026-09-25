from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.associations import bookmarks


async def create_bookmark(db: AsyncSession, user_id: int, task_id: int) -> bool:
    """Tra ve False neu user da bookmark task nay tu truoc.

    Dung 1 cau INSERT ... ON CONFLICT DO NOTHING thay vi check roi insert:
    2 request dong thoi khong the cung lot qua buoc check roi dam UNIQUE (500).
    """
    result = await db.execute(
        insert(bookmarks)
        .values(user_id=user_id, task_id=task_id)
        .on_conflict_do_nothing()
    )
    await db.commit()
    return result.rowcount > 0
