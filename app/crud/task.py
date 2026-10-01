from datetime import date, timedelta

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.constants import DUE_SOON_DAYS
from app.core.pagination import Pagination, paginate
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    return await db.get(Task, task_id)


async def get_task_with_assignee(db: AsyncSession, task_id: int) -> Task | None:
    return await db.get(Task, task_id, options=[joinedload(Task.assignee)])


async def get_tasks(
    db: AsyncSession,
    pagination: Pagination,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> tuple[list[Task], int]:
    query = select(Task).options(selectinload(Task.tags)).order_by(Task.id)
    if status is not None:
        query = query.where(Task.status == status)
    if priority is not None:
        query = query.where(Task.priority == priority)
    return await paginate(db, query, pagination)


async def get_tasks_by_project(
    db: AsyncSession, project_id: int, pagination: Pagination
) -> tuple[list[Task], int]:
    query = (
        select(Task)
        .where(Task.project_id == project_id)
        .options(selectinload(Task.tags))
        .order_by(Task.id)
    )
    return await paginate(db, query, pagination)


def _due_soon_conditions(today: date) -> list[ColumnElement[bool]]:
    # 1 dinh nghia "sap den han" duy nhat cho ca buoc quet lan buoc kiem tra lai
    # truoc khi gui mail (R33). due_date la date -> "trong 24h toi" = han tu hom
    # nay den het DUE_SOON_DAYS ngay toi.
    return [
        Task.status != TaskStatus.DONE,
        Task.assignee_id.is_not(None),
        Task.due_date >= today,
        Task.due_date <= today + timedelta(days=DUE_SOON_DAYS),
    ]


async def get_due_soon_task_ids(db: AsyncSession, today: date) -> list[int]:
    # Chi lay id: job quet chi can id de tach thanh tung job gui mail
    result = await db.scalars(
        select(Task.id).where(*_due_soon_conditions(today)).order_by(Task.id)
    )
    return list(result.all())


async def get_due_soon_task(db: AsyncSession, task_id: int, today: date) -> Task | None:
    return await db.scalar(
        select(Task)
        .options(joinedload(Task.assignee))
        .where(Task.id == task_id, *_due_soon_conditions(today))
    )


async def create_task(
    db: AsyncSession, project_id: int, data: TaskCreate, created_by: int
) -> Task:
    task = Task(project_id=project_id, created_by=created_by, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task, attribute_names=["tags"])
    return task


async def assign_task(db: AsyncSession, task: Task, assignee_id: int) -> Task:
    task.assignee_id = assignee_id
    await db.commit()
    await db.refresh(task, attribute_names=["assignee_id", "tags"])
    return task
