from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SEED_TAGS, TAGS_CACHE_KEY
from app.core.exceptions import ConflictException
from app.core.security import verify_password
from app.crud import user as crud_user
from app.models.project import Project
from app.models.tag import Tag
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services import seed as seed_service
from app.services import user as user_service
from tests.conftest import FakeRedis, make_user

PASSWORD = "SeedPass123"


def _options(
    users: int = 3, projects: int = 2, tasks_per_project: int = 4
) -> seed_service.SeedOptions:
    return seed_service.SeedOptions(
        users=users, projects=projects, tasks_per_project=tasks_per_project, password=PASSWORD
    )


async def _count(db: AsyncSession, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model))


# ---- seed ------------------------------------------------------------------


async def test_seed_creates_requested_data(
    db_session: AsyncSession, fake_redis: FakeRedis
) -> None:
    result = await seed_service.seed_data(db_session, fake_redis, _options())

    # 3 member + 1 PM moi project
    assert (result.users, result.projects, result.tasks, result.tags) == (5, 2, 8, len(SEED_TAGS))
    assert await _count(db_session, Task) == 8
    pms = (await db_session.scalars(select(User).where(User.role == UserRole.PM))).all()
    projects = (await db_session.scalars(select(Project).order_by(Project.id))).all()
    assert {p.manager_id for p in projects} == {pm.id for pm in pms}


async def test_seed_is_idempotent(db_session: AsyncSession, fake_redis: FakeRedis) -> None:
    await seed_service.seed_data(db_session, fake_redis, _options())
    counts = [await _count(db_session, m) for m in (User, Project, Task, Tag)]

    again = await seed_service.seed_data(db_session, fake_redis, _options())

    assert (again.users, again.projects, again.tasks, again.tags) == (0, 0, 0, 0)
    assert [await _count(db_session, m) for m in (User, Project, Task, Tag)] == counts


async def test_seed_with_bigger_numbers_only_adds_missing(
    db_session: AsyncSession, fake_redis: FakeRedis
) -> None:
    await seed_service.seed_data(db_session, fake_redis, _options(tasks_per_project=4))
    first_assignees = (
        await db_session.scalars(select(Task.assignee_id).order_by(Task.id))
    ).all()

    result = await seed_service.seed_data(
        db_session, fake_redis, _options(users=4, tasks_per_project=6)
    )

    assert (result.users, result.projects, result.tasks) == (1, 0, 4)
    assert await _count(db_session, Task) == 12
    # Task da co khong bi sua
    assert (
        await db_session.scalars(select(Task.assignee_id).order_by(Task.id).limit(8))
    ).all() == first_assignees


async def test_seed_assigns_tasks_round_robin_to_members_without_mail(
    db_session: AsyncSession, fake_redis: FakeRedis, celery_delay: dict[str, MagicMock]
) -> None:
    await seed_service.seed_data(db_session, fake_redis, _options(users=2, projects=1))

    members = (
        await db_session.scalars(
            select(User.id).where(User.role == UserRole.MEMBER).order_by(User.username)
        )
    ).all()
    assignees = (await db_session.scalars(select(Task.assignee_id).order_by(Task.title))).all()
    assert assignees == [members[0], members[1], members[0], members[1]]
    assert not celery_delay["send_assign_notification"].called


async def test_seed_users_can_login_with_given_password(
    db_session: AsyncSession, fake_redis: FakeRedis
) -> None:
    await seed_service.seed_data(db_session, fake_redis, _options(users=1, projects=0))
    user = await crud_user.get_user_by_username(db_session, "seed_member_001")
    assert user is not None
    assert verify_password(PASSWORD, user.hashed_password)


async def test_seed_without_members_leaves_tasks_unassigned(
    db_session: AsyncSession, fake_redis: FakeRedis
) -> None:
    await seed_service.seed_data(db_session, fake_redis, _options(users=0, projects=1))
    assert set((await db_session.scalars(select(Task.assignee_id))).all()) == {None}


async def test_seed_invalidates_tags_cache(
    db_session: AsyncSession, fake_redis: FakeRedis
) -> None:
    fake_redis.store[TAGS_CACHE_KEY] = "[]"
    await seed_service.seed_data(db_session, fake_redis, _options(users=0, projects=0))
    assert TAGS_CACHE_KEY not in fake_redis.store


# ---- create-admin ----------------------------------------------------------


def _admin_data(username: str = "root", email: str = "root@taskhub.dev") -> UserCreate:
    return UserCreate(username=username, email=email, full_name="Root", password="Admin12345")


async def test_create_admin(db_session: AsyncSession) -> None:
    admin, created = await user_service.create_admin(db_session, _admin_data())
    assert created is True
    assert admin.role == UserRole.ADMIN
    assert verify_password("Admin12345", admin.hashed_password)


async def test_create_admin_again_is_noop(db_session: AsyncSession) -> None:
    first, _ = await user_service.create_admin(db_session, _admin_data())
    data = _admin_data().model_copy(update={"password": "Different123"})

    again, created = await user_service.create_admin(db_session, data)

    assert created is False
    assert again.id == first.id
    # Khong am tham doi password admin dang co
    assert verify_password("Admin12345", again.hashed_password)


async def test_create_admin_rejects_username_of_non_admin(db_session: AsyncSession) -> None:
    await make_user(db_session, "root")
    with pytest.raises(ConflictException):
        await user_service.create_admin(db_session, _admin_data())


async def test_create_admin_rejects_taken_email(db_session: AsyncSession) -> None:
    await make_user(db_session, "someone")
    with pytest.raises(ConflictException):
        await user_service.create_admin(db_session, _admin_data(email="someone@example.com"))
