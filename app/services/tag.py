"""Nghiep vu tag + cache Redis cho GET /tags (cache-aside, R13).

Cache chi la toi uu, khong phai nguon du lieu: Redis loi thi bo qua cache va
doc/ghi thang DB (fail-open), khong lam hong request (R41).
Moi trang (skip/limit) la 1 field trong cung 1 Redis hash -> invalidate chi
can xoa 1 key la mat het moi trang. Invalidate ngay sau khi commit
create/update/delete (BP24); TTL chi la luoi an toan khi invalidate that bai.
"""

import logging

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import TAGS_CACHE_KEY
from app.core.pagination import Pagination
from app.crud import tag as crud_tag
from app.models.tag import Tag
from app.schemas.base import Page
from app.schemas.tag import TagCreate, TagRead, TagUpdate

logger = logging.getLogger(__name__)
TagPage = Page[TagRead]


def _page_field(pagination: Pagination) -> str:
    return f"{pagination.skip}:{pagination.limit}"


async def _read_cache(redis: Redis, pagination: Pagination) -> TagPage | None:
    try:
        raw = await redis.hget(TAGS_CACHE_KEY, _page_field(pagination))
    except RedisError:
        logger.warning("Redis unavailable, reading tags from DB", exc_info=True)
        return None
    if raw is None:
        return None
    try:
        return TagPage.model_validate_json(raw)
    except ValidationError:
        # Du lieu cache cu khong con khop schema (vd TagRead vua them field) -> coi nhu miss
        logger.warning("Invalid tags cache payload, reading tags from DB")
        return None


async def _write_cache(redis: Redis, pagination: Pagination, page: TagPage) -> None:
    try:
        await redis.hset(TAGS_CACHE_KEY, _page_field(pagination), page.model_dump_json())
        # nx: TTL tinh tu lan ghi dau, trang ghi sau khong keo dai tuoi cache cu
        await redis.expire(TAGS_CACHE_KEY, settings.tag_cache_ttl_seconds, nx=True)
    except RedisError:
        logger.warning("Redis unavailable, skip caching tags", exc_info=True)


async def invalidate_tags_cache(redis: Redis) -> None:
    # Goi sau commit: loi o day khong duoc lam hong response da thanh cong (R32);
    # cache cu se tu het han sau TAG_CACHE_TTL_SECONDS
    try:
        await redis.delete(TAGS_CACHE_KEY)
    except RedisError:
        logger.exception("Failed to invalidate tags cache, stale until TTL expires")


async def list_tags(db: AsyncSession, redis: Redis, pagination: Pagination) -> TagPage:
    cached = await _read_cache(redis, pagination)
    if cached is not None:
        return cached
    tags, total = await crud_tag.get_tags(db, pagination)
    page = TagPage(items=[TagRead.model_validate(t) for t in tags], total=total)
    await _write_cache(redis, pagination, page)
    return page


async def create_tag(db: AsyncSession, redis: Redis, data: TagCreate) -> Tag:
    tag = await crud_tag.create_tag(db, data)
    await invalidate_tags_cache(redis)
    return tag


async def update_tag(db: AsyncSession, redis: Redis, tag: Tag, data: TagUpdate) -> Tag:
    updated = await crud_tag.update_tag(db, tag, data)
    await invalidate_tags_cache(redis)
    return updated


async def delete_tag(db: AsyncSession, redis: Redis, tag: Tag) -> None:
    await crud_tag.delete_tag(db, tag)
    await invalidate_tags_cache(redis)
