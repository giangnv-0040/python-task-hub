from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagination, paginate
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


async def get_tag(db: AsyncSession, tag_id: int) -> Tag | None:
    return await db.get(Tag, tag_id)


async def get_tags(db: AsyncSession, pagination: Pagination) -> tuple[list[Tag], int]:
    return await paginate(db, select(Tag).order_by(Tag.id), pagination)


async def create_tag(db: AsyncSession, data: TagCreate) -> Tag:
    tag = Tag(**data.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, tag: Tag, data: TagUpdate) -> Tag:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    await db.delete(tag)
    await db.commit()
