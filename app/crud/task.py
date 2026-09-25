from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.task import Task
from app.schemas.task import TaskCreate


async def get_tasks_by_project(db: AsyncSession, project_id: int) -> list[Task]:
    result = await db.execute(
        select(Task).where(Task.project_id == project_id).options(joinedload(Task.tags))
    )
    return list(result.unique().scalars().all())


async def create_task(db: AsyncSession, project_id: int, data: TaskCreate) -> Task:
    task = Task(project_id=project_id, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task, attribute_names=["tags"])
    return task
