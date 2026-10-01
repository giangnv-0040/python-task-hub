from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.cache import RedisDep
from app.core.constants import (
    ADMIN_ONLY_RESPONSES,
    TAG_NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.core.deps import DbSession, get_current_active_user, verify_admin_role
from app.core.exceptions import NotFoundException
from app.core.messages import TAG_NOT_FOUND
from app.crud import tag as crud_tag
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services import tag as tag_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


async def get_tag_detail(tag_id: int, db: DbSession) -> Tag:
    tag = await crud_tag.get_tag(db, tag_id)
    if tag is None:
        raise NotFoundException(TAG_NOT_FOUND)
    return tag


TagDetailDep = Annotated[Tag, Depends(get_tag_detail)]


@router.get(
    "",
    response_model=list[TagRead],
    summary="Danh sách tag (cache Redis)",
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(get_current_active_user)],
)
async def list_tags(db: DbSession, redis: RedisDep) -> list[TagRead]:
    return await tag_service.list_tags(db, redis)


@router.post(
    "",
    response_model=TagRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tag mới (chỉ Admin)",
    responses=ADMIN_ONLY_RESPONSES,
    dependencies=[Depends(verify_admin_role)],
)
async def create_tag(data: TagCreate, db: DbSession, redis: RedisDep) -> TagRead:
    tag = await tag_service.create_tag(db, redis, data)
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
    tag: TagDetailDep,
    db: DbSession,
    redis: RedisDep,
) -> TagRead:
    updated = await tag_service.update_tag(db, redis, tag, data)
    return TagRead.model_validate(updated)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá tag (chỉ Admin)",
    responses={**ADMIN_ONLY_RESPONSES, **TAG_NOT_FOUND_RESPONSE},
    dependencies=[Depends(verify_admin_role)],
)
async def delete_tag(tag: TagDetailDep, db: DbSession, redis: RedisDep) -> None:
    await tag_service.delete_tag(db, redis, tag)
