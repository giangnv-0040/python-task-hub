from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import task as crud_task
from app.database import get_db
from app.models.project import Project
from app.routers.projects import get_project_detail
from app.schemas.task import TaskCreate, TaskRead

# Router rieng cho task nested duoi project (khac router "/api/tasks" o duoi):
# route nay thao tac chinh tren Task, chi nested URL duoi /projects vi ly do
# path, nen van dat trong file tasks.py (R18) thay vi projects.py.
project_tasks_router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@project_tasks_router.get(
    "",
    response_model=list[TaskRead],
    summary="Danh sách task trong project",
    responses={404: {"description": "Project không tồn tại"}},
)
async def list_project_tasks(
    project: Project = Depends(get_project_detail),
    db: AsyncSession = Depends(get_db),
) -> list[TaskRead]:
    tasks = await crud_task.get_tasks_by_project(db, project.id)
    return [TaskRead.model_validate(t) for t in tasks]


@project_tasks_router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo task trong project",
    responses={404: {"description": "Project không tồn tại"}},
)
async def create_project_task(
    data: TaskCreate,
    project: Project = Depends(get_project_detail),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    task = await crud_task.create_task(db, project.id, data)
    return TaskRead.model_validate(task)
