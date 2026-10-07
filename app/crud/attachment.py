from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagination, paginate
from app.models.attachment import Attachment


async def get_attachment(db: AsyncSession, attachment_id: int) -> Attachment | None:
    return await db.get(Attachment, attachment_id)


async def get_attachments_by_task(
    db: AsyncSession, task_id: int, pagination: Pagination
) -> tuple[list[Attachment], int]:
    query = select(Attachment).where(Attachment.task_id == task_id).order_by(Attachment.id)
    return await paginate(db, query, pagination)


async def create_attachment(
    db: AsyncSession,
    task_id: int,
    uploaded_by: int,
    filename: str,
    storage_key: str,
    content_type: str,
    size: int,
) -> Attachment:
    attachment = Attachment(
        task_id=task_id,
        uploaded_by=uploaded_by,
        filename=filename,
        storage_key=storage_key,
        content_type=content_type,
        size=size,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


async def delete_attachment(db: AsyncSession, attachment: Attachment) -> None:
    await db.delete(attachment)
    await db.commit()
