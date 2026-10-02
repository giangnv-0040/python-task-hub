"""Chay CLI qua Typer CliRunner tren DB test (du lieu commit that -> dung
fixture committed_session de don sach sau test)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import Result
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from typer.testing import CliRunner

from app import cli
from app.models.task import Task
from app.models.user import User, UserRole
from tests.conftest import FakeRedis

runner = CliRunner()


async def _invoke(*args: str) -> Result:
    # CLI tu goi asyncio.run() -> chay tren thread rieng, ngoai event loop cua test
    return await asyncio.to_thread(runner.invoke, cli.cli, list(args))


@pytest.fixture
def cli_db(
    engine: AsyncEngine, committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> AsyncSession:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    # Khong dispose engine that cua app (pool cua DB dev)
    monkeypatch.setattr(cli, "engine", AsyncMock())
    monkeypatch.setattr(cli, "get_redis", FakeRedis)
    return committed_session


async def test_seed_command_twice(cli_db: AsyncSession) -> None:
    args = ["seed", "--users", "2", "--projects", "1", "--tasks-per-project", "3"]
    first = await _invoke(*args)
    second = await _invoke(*args)

    assert first.exit_code == 0, first.output
    assert "3 users, 1 projects, 3 tasks" in first.output
    assert "0 users, 0 projects, 0 tasks, 0 tags" in second.output
    assert await cli_db.scalar(select(func.count()).select_from(Task)) == 3


async def test_create_admin_command(cli_db: AsyncSession) -> None:
    result = await _invoke(
        "create-admin",
        *("--username", "root"),
        *("--email", "root@taskhub.dev"),
        *("--password", "Admin12345"),
    )

    assert result.exit_code == 0, result.output
    admin = await cli_db.scalar(select(User).where(User.username == "root"))
    assert admin is not None
    assert admin.role == UserRole.ADMIN


async def test_create_admin_command_invalid_input_exits_1(cli_db: AsyncSession) -> None:
    result = await _invoke(
        "create-admin", "--username", "root", "--email", "not-an-email", "--password", "short"
    )

    assert result.exit_code == 1
    assert "email" in result.output
    assert await cli_db.scalar(select(func.count()).select_from(User)) == 0


def test_seed_rejects_negative_numbers() -> None:
    result = runner.invoke(cli.cli, ["seed", "--users", "-1"])
    assert result.exit_code == 2


def test_reset_db_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    run = MagicMock()
    monkeypatch.setattr(cli, "_run", run)

    result = runner.invoke(cli.cli, ["reset-db"], input="n\n")

    assert result.exit_code == 1
    run.assert_not_called()
