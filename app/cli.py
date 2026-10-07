"""CLI quan tri TaskHub (Ngay 8): `python -m app.cli <command>`.

    python -m app.cli seed --users 10 --projects 3 --tasks-per-project 10
    python -m app.cli create-admin --username admin --email admin@taskhub.dev
    python -m app.cli reset-db --yes
"""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, TypeVar

import typer
from alembic import command
from alembic.config import Config as AlembicConfig
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import get_redis
from app.core.constants import (
    SEED_DEFAULT_PASSWORD,
    SEED_DEFAULT_PROJECTS,
    SEED_DEFAULT_TASKS_PER_PROJECT,
    SEED_DEFAULT_USERS,
)
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.messages import (
    CLI_ADMIN_ALREADY_EXISTS,
    CLI_ADMIN_CREATED,
    CLI_RESET_DB_CONFIRM,
    CLI_RESET_DB_DONE,
    CLI_SEED_DONE,
)
from app.database import SessionLocal, engine
from app.schemas.user import UserCreate
from app.services import seed as seed_service
from app.services import tag as tag_service
from app.services import user as user_service

T = TypeVar("T")

ALEMBIC_INI_PATH = Path(__file__).resolve().parent.parent / "alembic.ini"

cli = typer.Typer(help="TaskHub admin CLI", no_args_is_help=True)


@cli.callback()
def main() -> None:
    setup_logging()


def _run(fn: Callable[[AsyncSession, Redis], Awaitable[T]]) -> T:
    """Chay 1 thao tac async voi session DB + Redis, loi nghiep vu/validate in
    ra stderr va exit 1 thay vi stacktrace."""

    async def _main() -> T:
        redis = get_redis()
        try:
            async with SessionLocal() as db:
                return await fn(db, redis)
        finally:
            await redis.aclose()
            await engine.dispose()

    try:
        return asyncio.run(_main())
    except (AppException, ValidationError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None


@cli.command()
def seed(
    users: Annotated[int, typer.Option(min=0, help="So user MEMBER")] = SEED_DEFAULT_USERS,
    projects: Annotated[
        int, typer.Option(min=0, help="So project (moi project co 1 PM rieng)")
    ] = SEED_DEFAULT_PROJECTS,
    tasks_per_project: Annotated[
        int, typer.Option(min=0, help="So task moi project")
    ] = SEED_DEFAULT_TASKS_PER_PROJECT,
    password: Annotated[
        str, typer.Option(help="Password cua moi user seed")
    ] = SEED_DEFAULT_PASSWORD,
) -> None:
    """Tao du lieu mau (idempotent: chay lai khong tao trung)."""
    options = seed_service.SeedOptions(
        users=users, projects=projects, tasks_per_project=tasks_per_project, password=password
    )
    result = _run(lambda db, redis: seed_service.seed_data(db, redis, options))
    typer.echo(
        CLI_SEED_DONE.format(
            users=result.users, projects=result.projects, tasks=result.tasks, tags=result.tags
        )
    )


@cli.command("create-admin")
def create_admin(
    username: Annotated[str, typer.Option(prompt=True)],
    email: Annotated[str, typer.Option(prompt=True)],
    password: Annotated[
        str, typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)
    ],
    full_name: Annotated[str, typer.Option(help="Mac dinh = username")] = "",
) -> None:
    """Tao tai khoan ADMIN (register qua API luon la MEMBER)."""

    async def _create(db: AsyncSession, _: Redis) -> tuple[str, bool]:
        # Validate trong _run de loi schema cung in gon nhu loi nghiep vu
        data = UserCreate(
            username=username, email=email, full_name=full_name or username, password=password
        )
        admin, created = await user_service.create_admin(db, data)
        return admin.username, created

    admin_username, created = _run(_create)
    message = CLI_ADMIN_CREATED if created else CLI_ADMIN_ALREADY_EXISTS
    typer.echo(message.format(username=admin_username))


@cli.command("reset-db")
def reset_db(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Bo qua buoc xac nhan")] = False,
) -> None:
    """Xoa toan bo schema roi chay lai migration tu dau (chi dung khi dev)."""
    if not yes:
        database = make_url(settings.database_url).render_as_string(hide_password=True)
        typer.confirm(CLI_RESET_DB_CONFIRM.format(database=database), abort=True)

    async def _drop_schema(db: AsyncSession, redis: Redis) -> None:
        # DROP SCHEMA xoa ca bang alembic_version va enum type -> upgrade head
        # tao lai dung nhu DB moi, khong phu thuoc downgrade() cua tung migration
        await db.execute(text("DROP SCHEMA public CASCADE"))
        await db.execute(text("CREATE SCHEMA public"))
        await db.commit()
        await tag_service.invalidate_tags_cache(redis)

    _run(_drop_schema)
    # Ngoai asyncio.run o tren: alembic/env.py tu goi asyncio.run() rieng
    command.upgrade(AlembicConfig(str(ALEMBIC_INI_PATH)), "head")
    typer.echo(CLI_RESET_DB_DONE)


if __name__ == "__main__":
    cli()
