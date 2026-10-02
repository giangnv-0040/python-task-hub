from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.cache import get_redis
from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models.project import Project
from app.models.task import Task
from app.models.user import User, UserRole
from app.storage import get_storage
from app.storage.local import LocalStorage
from app.worker import db as worker_db
from app.worker import tasks as worker_tasks

DEFAULT_TEST_PASSWORD = "Password123"
# bcrypt co tinh cham (~0.2s/lan): hash 1 lan dung chung cho moi user test
_DEFAULT_TEST_PASSWORD_HASH = hash_password(DEFAULT_TEST_PASSWORD)


def _test_database_url() -> str:
    # TEST_DATABASE_URL trong .env; neu chua khai bao thi suy ra tu DATABASE_URL
    # bang cach them hau to "_test" vao ten DB (khong dung chung DB voi app that).
    if settings.test_database_url:
        return settings.test_database_url
    base, _, db_name = settings.database_url.rpartition("/")
    return f"{base}/{db_name}_test"


class FakeRedis:
    """Thay Redis that trong test (chi cac lenh app dung): khong can Redis chay,
    va bat `fail=True` de gia lap Redis sap."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, str]] = {}
        self.ttl: dict[str, int] = {}
        self.fail = False

    def _check(self) -> None:
        if self.fail:
            raise RedisConnectionError("fake redis is down")

    async def hget(self, key: str, field: str) -> str | None:
        self._check()
        return self.store.get(key, {}).get(field)

    async def hset(self, key: str, field: str, value: str) -> None:
        self._check()
        self.store.setdefault(key, {})[field] = value

    async def expire(self, key: str, seconds: int, nx: bool = False) -> None:
        self._check()
        if not (nx and key in self.ttl):
            self.ttl[key] = seconds

    async def delete(self, key: str) -> None:
        self._check()
        self.store.pop(key, None)
        self.ttl.pop(key, None)

    async def aclose(self) -> None:
        pass


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    # NullPool: test async (loop cua pytest) va test Celery task (asyncio.run tren
    # thread rieng) cung dung engine nay -> khong giu connection giua 2 loop
    test_engine = create_async_engine(_test_database_url(), poolclass=NullPool)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    # Moi test chay trong 1 transaction rieng, code goi db.commit() chi commit
    # SAVEPOINT; cuoi test rollback het -> test khong anh huong nhau.
    connection = await engine.connect()
    trans = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, fake_redis: FakeRedis, tmp_path: Path
) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    # File dinh kem ghi vao thu muc tam cua test, khong dung storage that
    app.dependency_overrides[get_storage] = lambda: LocalStorage(str(tmp_path))
    transport = ASGITransport(app=app)
    # base_url mang san API_PREFIX (/api/v1): test goi path tuong doi "/tasks"...,
    # doi version API khong phai sua tung test
    async with AsyncClient(
        transport=transport, base_url=f"http://test{settings.api_prefix}"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def celery_delay(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Test khong can Redis/Celery worker: mock .delay() (SPEC Ngay 7). Test nao
    can kiem tra job da duoc day len thi nhan fixture nay de assert."""
    mocks = {}
    for job in (
        worker_tasks.send_comment_notification,
        worker_tasks.send_assign_notification,
        worker_tasks.send_due_reminder,
    ):
        mocks[job.name.rsplit(".", 1)[-1]] = mock = MagicMock()
        monkeypatch.setattr(job, "delay", mock)
    return mocks


@pytest_asyncio.fixture
async def committed_session(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncSession, None]:
    """Cho test chay than Celery task that: run_with_session tu mo session rieng
    qua app.worker.db.WorkerSession (tro ve DB test o day), tren connection khac
    -> du lieu phai COMMIT that, khong nam trong transaction nhu db_session.
    Don sach DB sau test."""
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(worker_db, "WorkerSession", session_factory)
    async with session_factory() as session:
        yield session
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def make_user(
    db_session: AsyncSession,
    username: str,
    role: UserRole = UserRole.MEMBER,
    password: str = DEFAULT_TEST_PASSWORD,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.capitalize(),
        hashed_password=(
            _DEFAULT_TEST_PASSWORD_HASH
            if password == DEFAULT_TEST_PASSWORD
            else hash_password(password)
        ),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def make_project(
    db_session: AsyncSession, name: str = "Project", manager: User | None = None
) -> Project:
    project = Project(name=name, manager_id=manager.id if manager else None)
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


async def make_task(
    db_session: AsyncSession, project: Project, creator: User, **fields: object
) -> Task:
    task = Task(project_id=project.id, created_by=creator.id, **{"title": "Task", **fields})
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    return await make_user(db_session, "admin1", role=UserRole.ADMIN)


@pytest_asyncio.fixture
async def pm_user(db_session: AsyncSession) -> User:
    return await make_user(db_session, "pm1", role=UserRole.PM)


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession) -> User:
    return await make_user(db_session, "member1", role=UserRole.MEMBER)
