"""Nghiep vu tag + cache Redis cho GET /api/tags (cache-aside, R13).

Cache chi la toi uu, khong phai nguon du lieu: Redis loi thi bo qua cache va
doc/ghi thang DB (fail-open), khong lam hong request (R41).
Invalidate ngay sau khi commit create/update/delete (BP24); TTL chi la luoi an
toan cho truong hop invalidate that bai.
"""

import logging

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import TAGS_CACHE_KEY
from app.crud import tag as crud_tag
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate

logger = logging.getLogger(__name__)
_tag_list_adapter = TypeAdapter(list[TagRead])


async def _read_cache(redis: Redis) -> list[TagRead] | None:
    try:
        raw = await redis.get(TAGS_CACHE_KEY)
    except RedisError:
        logger.warning("Redis unavailable, reading tags from DB", exc_info=True)
        return None
    if raw is None:
        return None
    try:
        return _tag_list_adapter.validate_json(raw)
    except ValidationError:
        # Du lieu cache cu khong con khop schema (vd TagRead vua them field) -> coi nhu miss
        logger.warning("Invalid tags cache payload, reading tags from DB")
        return None


async def _write_cache(redis: Redis, tags: list[TagRead]) -> None:
    try:
        await redis.set(
            TAGS_CACHE_KEY,
            _tag_list_adapter.dump_json(tags),
            ex=settings.tag_cache_ttl_seconds,
        )
    except RedisError:
        logger.warning("Redis unavailable, skip caching tags", exc_info=True)


async def _invalidate_cache(redis: Redis) -> None:
    # Goi sau commit: loi o day khong duoc lam hong response da thanh cong (R32);
    # cache cu se tu het han sau TAG_CACHE_TTL_SECONDS
    try:
        await redis.delete(TAGS_CACHE_KEY)
    except RedisError:
        logger.exception("Failed to invalidate tags cache, stale until TTL expires")


async def list_tags(db: AsyncSession, redis: Redis) -> list[TagRead]:
    cached = await _read_cache(redis)
    if cached is not None:
        return cached
    tags = [TagRead.model_validate(t) for t in await crud_tag.get_tags(db)]
    await _write_cache(redis, tags)
    return tags


async def create_tag(db: AsyncSession, redis: Redis, data: TagCreate) -> Tag:
    tag = await crud_tag.create_tag(db, data)
    await _invalidate_cache(redis)
    return tag


async def update_tag(db: AsyncSession, redis: Redis, tag: Tag, data: TagUpdate) -> Tag:
    updated = await crud_tag.update_tag(db, tag, data)
    await _invalidate_cache(redis)
    return updated


async def delete_tag(db: AsyncSession, redis: Redis, tag: Tag) -> None:
    await crud_tag.delete_tag(db, tag)
    await _invalidate_cache(redis)
