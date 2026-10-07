"""Nghiep vu task: tao/assign task + bao assignee qua Celery trong 1 cho (R13)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import task as crud_task
from app.models.task import Task
from app.schemas.task import TaskCreate
from app.services import notification as notification_service


async def create_task(
    db: AsyncSession, project_id: int, data: TaskCreate, created_by: int
) -> Task:
    task = await crud_task.create_task(db, project_id, data, created_by=created_by)
    # Tao task kem assignee cung la 1 lan assign -> bao nguoi duoc giao
    if task.assignee_id is not None:
        await notification_service.notify_task_assigned(task, assigned_by=created_by)
    return task


async def assign_task(
    db: AsyncSession, task: Task, assignee_id: int, assigned_by: int
) -> Task:
    updated = await crud_task.assign_task(db, task, assignee_id)
    await notification_service.notify_task_assigned(updated, assigned_by=assigned_by)
    return updated
