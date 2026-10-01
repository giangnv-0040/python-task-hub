"""Session DB cho Celery worker.

Celery task la ham sync; moi lan chay goi `asyncio.run()` -> 1 event loop moi.
Connection asyncpg gan voi event loop da tao ra no, nen KHONG dung chung pool
cua `app.database.engine` (connection trong pool thuoc loop cu da dong -> loi
tu task thu 2 tro di). NullPool: moi session mo connection moi va dong ngay.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

T = TypeVar("T")

worker_engine = create_async_engine(
    settings.database_url, echo=settings.db_echo, poolclass=NullPool
)
WorkerSession = async_sessionmaker(bind=worker_engine, expire_on_commit=False)


def run_with_session(fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Chay 1 ham async nhan AsyncSession tu code sync (than Celery task)."""

    async def _run() -> T:
        async with WorkerSession() as db:
            return await fn(db)

    return asyncio.run(_run())
