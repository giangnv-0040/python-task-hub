from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    PERMISSION_RESPONSES,
    PROJECT_ASSIGNEE_NOT_FOUND_RESPONSE,
    PROJECT_NOT_FOUND_RESPONSE,
    TASK_NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.core.deps import (
    get_current_active_user,
    get_project_detail,
    get_task_detail,
    verify_project_manager,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.core.messages import ASSIGNEE_NOT_FOUND, TASK_ALREADY_BOOKMARKED
from app.core.pagination import PaginationDep
from app.crud import bookmark as crud_bookmark
from app.crud import task as crud_task
from app.crud import user as crud_user
from app.database import get_db
from app.models.project import Project
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead

# Router rieng cho task nested duoi project (khac router "/api/tasks" o duoi):
# route nay thao tac chinh tren Task, chi nested URL duoi /projects vi ly do
# path, nen van dat trong file tasks.py (R18) thay vi projects.py.
project_tasks_router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _ensure_valid_assignee(db: AsyncSession, assignee_id: int | None) -> None:
    # id khong ton tai gay loi FK (500) o DB; user bi khoa khong nen nhan task moi
    if assignee_id is None:
        return
    assignee = await crud_user.get_user(db, assignee_id)
    if assignee is None or not assignee.is_active:
        raise NotFoundException(ASSIGNEE_NOT_FOUND)


@project_tasks_router.get(
    "",
    response_model=list[TaskRead],
    summary="Danh sách task trong project (phân trang)",
    responses={**UNAUTHORIZED_RESPONSE, **PROJECT_NOT_FOUND_RESPONSE},
    dependencies=[Depends(get_current_active_user)],
)
async def list_project_tasks(
    pagination: PaginationDep,
    project: Project = Depends(get_project_detail),
    db: AsyncSession = Depends(get_db),
) -> list[TaskRead]:
    tasks = await crud_task.get_tasks_by_project(db, project.id, pagination)
    return [TaskRead.model_validate(t) for t in tasks]


@project_tasks_router.post(
    "",
    response_model=TaskRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Tạo task trong project",
    responses={**PERMISSION_RESPONSES, **PROJECT_ASSIGNEE_NOT_FOUND_RESPONSE},
)
async def create_project_task(
    data: TaskCreate,
    project: Project = Depends(verify_project_manager),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    await _ensure_valid_assignee(db, data.assignee_id)
    task = await crud_task.create_task(db, project.id, data, created_by=current_user.id)
    return TaskRead.model_validate(task)


@router.get(
    "",
    response_model=list[TaskRead],
    summary="Danh sách task (lọc theo status/priority, phân trang)",
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(get_current_active_user)],
)
async def list_tasks(
    pagination: PaginationDep,
    db: AsyncSession = Depends(get_db),
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
) -> list[TaskRead]:
    tasks = await crud_task.get_tasks(db, pagination, status=status, priority=priority)
    return [TaskRead.model_validate(t) for t in tasks]


@router.post(
    "/{task_id}/bookmark",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Bookmark 1 task",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **TASK_NOT_FOUND_RESPONSE,
        409: {"description": "Đã bookmark task này rồi"},
    },
)
async def bookmark_task(
    current_user: User = Depends(get_current_active_user),
    task: Task = Depends(get_task_detail),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await crud_bookmark.create_bookmark(db, current_user.id, task.id):
        raise ConflictException(TASK_ALREADY_BOOKMARKED)
