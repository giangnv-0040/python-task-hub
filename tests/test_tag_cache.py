from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TAGS_CACHE_KEY
from app.crud import tag as crud_tag
from app.models.user import User
from app.schemas.tag import TagCreate
from tests.conftest import FakeRedis, auth_headers


async def _list_tag_names(client: AsyncClient, user: User) -> list[str]:
    resp = await client.get("/api/tags", headers=auth_headers(user))
    assert resp.status_code == 200
    return [t["name"] for t in resp.json()]


async def test_list_tags_is_served_from_cache_after_first_call(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis, member_user: User
) -> None:
    await crud_tag.create_tag(db_session, TagCreate(name="backend", color="blue"))

    assert await _list_tag_names(client, member_user) == ["backend"]
    assert TAGS_CACHE_KEY in fake_redis.store

    # Ghi thang DB (khong qua API) -> cache khong biet, van tra ban da cache
    await crud_tag.create_tag(db_session, TagCreate(name="sneaky", color="red"))
    assert await _list_tag_names(client, member_user) == ["backend"]


async def test_tag_changes_via_api_invalidate_cache(
    client: AsyncClient, fake_redis: FakeRedis, admin_user: User
) -> None:
    headers = auth_headers(admin_user)
    assert await _list_tag_names(client, admin_user) == []

    created = await client.post("/api/tags", json={"name": "a", "color": "red"}, headers=headers)
    assert created.status_code == 201
    assert TAGS_CACHE_KEY not in fake_redis.store
    assert await _list_tag_names(client, admin_user) == ["a"]

    tag_id = created.json()["id"]
    await client.patch(f"/api/tags/{tag_id}", json={"name": "b"}, headers=headers)
    assert await _list_tag_names(client, admin_user) == ["b"]

    await client.delete(f"/api/tags/{tag_id}", headers=headers)
    assert await _list_tag_names(client, admin_user) == []


async def test_tags_still_work_when_redis_is_down(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis, admin_user: User
) -> None:
    fake_redis.fail = True
    await crud_tag.create_tag(db_session, TagCreate(name="backend", color="blue"))

    assert await _list_tag_names(client, admin_user) == ["backend"]
    created = await client.post(
        "/api/tags", json={"name": "new", "color": "red"}, headers=auth_headers(admin_user)
    )
    assert created.status_code == 201


async def test_invalid_cache_payload_falls_back_to_db(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis, admin_user: User
) -> None:
    await crud_tag.create_tag(db_session, TagCreate(name="backend", color="blue"))
    fake_redis.store[TAGS_CACHE_KEY] = '[{"unexpected": "shape"}]'

    assert await _list_tag_names(client, admin_user) == ["backend"]
