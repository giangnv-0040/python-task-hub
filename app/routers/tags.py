from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ADMIN_ONLY_RESPONSES,
    TAG_NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.core.deps import get_current_active_user, verify_admin_role
from app.core.exceptions import NotFoundException
from app.core.messages import TAG_NOT_FOUND
from app.crud import tag as crud_tag
from app.database import get_db
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


async def get_tag_detail(tag_id: int, db: AsyncSession = Depends(get_db)) -> Tag:
    tag = await crud_tag.get_tag(db, tag_id)
    if tag is None:
        raise NotFoundException(TAG_NOT_FOUND)
    return tag


@router.get(
    "",
    response_model=list[TagRead],
    summary="Danh sách tag",
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(get_current_active_user)],
)
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[TagRead]:
    tags = await crud_tag.get_tags(db)
    return [TagRead.model_validate(t) for t in tags]


@router.post(
    "",
    response_model=TagRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tag mới (chỉ Admin)",
    responses=ADMIN_ONLY_RESPONSES,
    dependencies=[Depends(verify_admin_role)],
)
async def create_tag(data: TagCreate, db: AsyncSession = Depends(get_db)) -> TagRead:
    tag = await crud_tag.create_tag(db, data)
    return TagRead.model_validate(tag)


# Tag dung chung cho moi project -> chi Admin duoc tao/sua/xoa (SPEC: PM chi co
# quyen tren project minh quan ly, Member khong co quyen tren tag)
@router.patch(
    "/{tag_id}",
    response_model=TagRead,
    summary="Cập nhật tag (chỉ Admin)",
    responses={**ADMIN_ONLY_RESPONSES, **TAG_NOT_FOUND_RESPONSE},
    dependencies=[Depends(verify_admin_role)],
)
async def update_tag(
    data: TagUpdate,
    tag: Tag = Depends(get_tag_detail),
    db: AsyncSession = Depends(get_db),
) -> TagRead:
    updated = await crud_tag.update_tag(db, tag, data)
    return TagRead.model_validate(updated)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá tag (chỉ Admin)",
    responses={**ADMIN_ONLY_RESPONSES, **TAG_NOT_FOUND_RESPONSE},
    dependencies=[Depends(verify_admin_role)],
)
async def delete_tag(
    tag: Tag = Depends(get_tag_detail), db: AsyncSession = Depends(get_db)
) -> None:
    await crud_tag.delete_tag(db, tag)
