from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    return await db.get(Task, task_id)


async def get_tasks(
    db: AsyncSession,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
) -> list[Task]:
    query = select(Task).options(joinedload(Task.tags)).order_by(Task.id)
    if status is not None:
        query = query.where(Task.status == status)
    if priority is not None:
        query = query.where(Task.priority == priority)
    result = await db.execute(query)
    return list(result.unique().scalars().all())


async def get_tasks_by_project(
    db: AsyncSession, project_id: int, skip: int, limit: int
) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .options(joinedload(Task.tags))
        .order_by(Task.id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.unique().scalars().all())


async def create_task(db: AsyncSession, project_id: int, data: TaskCreate) -> Task:
    task = Task(project_id=project_id, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task, attribute_names=["tags"])
    return task
