from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_LIMIT, DEFAULT_SKIP, TAGS_CACHE_KEY
from app.crud import tag as crud_tag
from app.models.user import User
from app.schemas.tag import TagCreate
from tests.conftest import FakeRedis, auth_headers


async def _list_tag_names(client: AsyncClient, user: User, **params: int) -> list[str]:
    resp = await client.get("/tags", params=params, headers=auth_headers(user))
    assert resp.status_code == 200
    return [t["name"] for t in resp.json()["items"]]


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

    created = await client.post("/tags", json={"name": "a", "color": "red"}, headers=headers)
    assert created.status_code == 201
    assert TAGS_CACHE_KEY not in fake_redis.store
    assert await _list_tag_names(client, admin_user) == ["a"]

    tag_id = created.json()["id"]
    await client.patch(f"/tags/{tag_id}", json={"name": "b"}, headers=headers)
    assert await _list_tag_names(client, admin_user) == ["b"]

    await client.delete(f"/tags/{tag_id}", headers=headers)
    assert await _list_tag_names(client, admin_user) == []


async def test_tags_still_work_when_redis_is_down(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis, admin_user: User
) -> None:
    fake_redis.fail = True
    await crud_tag.create_tag(db_session, TagCreate(name="backend", color="blue"))

    assert await _list_tag_names(client, admin_user) == ["backend"]
    created = await client.post(
        "/tags", json={"name": "new", "color": "red"}, headers=auth_headers(admin_user)
    )
    assert created.status_code == 201


async def test_invalid_cache_payload_falls_back_to_db(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis, admin_user: User
) -> None:
    await crud_tag.create_tag(db_session, TagCreate(name="backend", color="blue"))
    fake_redis.store[TAGS_CACHE_KEY] = {
        f"{DEFAULT_SKIP}:{DEFAULT_LIMIT}": '{"unexpected": "shape"}'
    }

    assert await _list_tag_names(client, admin_user) == ["backend"]


async def test_each_page_is_cached_and_invalidated_together(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis, admin_user: User
) -> None:
    for name in ("a", "b", "c"):
        await crud_tag.create_tag(db_session, TagCreate(name=name, color="red"))

    assert await _list_tag_names(client, admin_user, skip=0, limit=2) == ["a", "b"]
    assert await _list_tag_names(client, admin_user, skip=2, limit=2) == ["c"]
    assert set(fake_redis.store[TAGS_CACHE_KEY]) == {"0:2", "2:2"}

    # 1 lan thay doi qua API xoa cache cua moi trang
    resp = await client.post(
        "/tags", json={"name": "d", "color": "red"}, headers=auth_headers(admin_user)
    )
    assert resp.status_code == 201
    assert TAGS_CACHE_KEY not in fake_redis.store
    assert await _list_tag_names(client, admin_user, skip=2, limit=2) == ["c", "d"]
