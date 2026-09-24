from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import tag as crud_tag
from app.database import get_db
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/api/tags", tags=["tags"])


async def get_tag_or_404(tag_id: int, db: AsyncSession = Depends(get_db)) -> Tag:
    tag = await crud_tag.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


@router.get("", response_model=list[TagRead])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[Tag]:
    return await crud_tag.get_tags(db)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(data: TagCreate, db: AsyncSession = Depends(get_db)) -> Tag:
    return await crud_tag.create_tag(db, data)


@router.patch("/{tag_id}", response_model=TagRead)
async def update_tag(
    data: TagUpdate,
    tag: Tag = Depends(get_tag_or_404),
    db: AsyncSession = Depends(get_db),
) -> Tag:
    return await crud_tag.update_tag(db, tag, data)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag: Tag = Depends(get_tag_or_404), db: AsyncSession = Depends(get_db)
) -> None:
    await crud_tag.delete_tag(db, tag)
