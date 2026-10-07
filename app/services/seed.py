"""Seed du lieu mau cho dev/demo (Ngay 8), goi tu `python -m app.cli seed`.

Idempotent: moi ban ghi seed co ten/username co dinh theo so thu tu (xem
SEED_* trong constants) -> chay lai chi tao phan con thieu, khong tao trung.
Tang so luong (vd `--tasks-per-project` lon hon) thi tao them; giam thi khong
xoa ban ghi da co.

Ghi qua CRUD/service + Pydantic schema nhu API (R13), khong ghi thang ORM. Goi
thang CRUD (khong qua services/task, services/comment) nen khong day mail
Celery khi assign task seed.
"""

import itertools
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.concurrency import run_in_threadpool
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    SEED_DUE_DATE_SPREAD_DAYS,
    SEED_EMAIL_DOMAIN,
    SEED_MEMBER_USERNAME,
    SEED_PM_USERNAME,
    SEED_PROJECT_NAME,
    SEED_TAGS,
    SEED_TASK_TITLE,
)
from app.core.exceptions import ConflictException
from app.core.messages import CLI_SEED_USER_CONFLICT
from app.core.security import hash_password
from app.crud import project as crud_project
from app.crud import tag as crud_tag
from app.crud import task as crud_task
from app.crud import user as crud_user
from app.models.project import Project
from app.models.task import TaskPriority
from app.models.user import User, UserRole
from app.schemas.project import ProjectCreate
from app.schemas.tag import TagCreate
from app.schemas.task import TaskCreate
from app.schemas.user import UserCreate
from app.services import tag as tag_service


@dataclass(frozen=True)
class SeedOptions:
    users: int
    projects: int
    tasks_per_project: int
    password: str


@dataclass
class SeedResult:
    users: int = 0
    projects: int = 0
    tasks: int = 0
    tags: int = 0


async def _ensure_users(
    db: AsyncSession,
    usernames: list[str],
    role: UserRole,
    password: str,
    result: SeedResult,
) -> list[User]:
    """Tra ve user theo dung thu tu `usernames`, tao user con thieu."""
    existing = {u.username: u for u in await crud_user.get_users_by_usernames(db, usernames)}
    for user in existing.values():
        # Username seed co the bi register tay qua API (role MEMBER) hoac bi
        # khoa -> khong dung lai lam PM/assignee, bao loi thay vi seed sai quyen
        if user.role != role or not user.is_active:
            raise ConflictException(
                CLI_SEED_USER_CONFLICT.format(username=user.username, role=role.value)
            )
    missing = [name for name in usernames if name not in existing]
    if missing:
        # bcrypt cham (~0.2s) va block CPU -> hash 1 lan dung chung cho moi
        # user moi, chay trong threadpool (R26)
        hashed_password = await run_in_threadpool(hash_password, password)
        for username in missing:
            data = UserCreate(
                username=username,
                email=f"{username}@{SEED_EMAIL_DOMAIN}",
                full_name=username.replace("_", " ").title(),
                password=password,
            )
            existing[username] = await crud_user.create_user(db, data, hashed_password, role)
            result.users += 1
    return [existing[name] for name in usernames]


async def _ensure_project(
    db: AsyncSession, index: int, manager: User, result: SeedResult
) -> Project:
    name = SEED_PROJECT_NAME.format(index=index)
    project = await crud_project.get_project_by_name(db, name)
    if project is None:
        project = await crud_project.create_project(
            db, ProjectCreate(name=name, description=name, manager_id=manager.id)
        )
        result.projects += 1
    return project


async def _ensure_tasks(
    db: AsyncSession,
    project: Project,
    manager: User,
    members: list[User],
    count: int,
    result: SeedResult,
) -> None:
    existing_titles = await crud_task.get_task_titles_by_project(db, project.id)
    priorities = itertools.cycle(TaskPriority)
    assignees = itertools.cycle(members) if members else itertools.repeat(None)
    today = date.today()
    for index in range(1, count + 1):
        # Luon xoay vong ca khi task da ton tai -> task thu N luon nhan cung
        # priority/assignee du chay seed bao nhieu lan
        priority, assignee = next(priorities), next(assignees)
        title = SEED_TASK_TITLE.format(index=index)
        if title in existing_titles:
            continue
        data = TaskCreate(
            title=title,
            priority=priority,
            due_date=today + timedelta(days=index % SEED_DUE_DATE_SPREAD_DAYS),
            assignee_id=assignee.id if assignee else None,
        )
        await crud_task.create_task(db, project.id, data, created_by=manager.id)
        result.tasks += 1


async def _ensure_tags(db: AsyncSession, redis: Redis, result: SeedResult) -> None:
    for name, color in SEED_TAGS:
        if await crud_tag.get_tag_by_name(db, name) is None:
            # Qua service de invalidate cache GET /tags
            await tag_service.create_tag(db, redis, TagCreate(name=name, color=color))
            result.tags += 1


async def seed_data(db: AsyncSession, redis: Redis, options: SeedOptions) -> SeedResult:
    """Tao `options.users` member + moi project 1 PM rieng lam manager; task
    cua project assign xoay vong cho cac member."""
    result = SeedResult()
    members = await _ensure_users(
        db,
        [SEED_MEMBER_USERNAME.format(index=i) for i in range(1, options.users + 1)],
        UserRole.MEMBER,
        options.password,
        result,
    )
    managers = await _ensure_users(
        db,
        [SEED_PM_USERNAME.format(index=i) for i in range(1, options.projects + 1)],
        UserRole.PM,
        options.password,
        result,
    )
    for index, manager in enumerate(managers, start=1):
        project = await _ensure_project(db, index, manager, result)
        await _ensure_tasks(db, project, manager, members, options.tasks_per_project, result)
    await _ensure_tags(db, redis, result)
    return result
