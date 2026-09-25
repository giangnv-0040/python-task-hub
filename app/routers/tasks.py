from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.exceptions import ConflictException, NotFoundException
from app.core.messages import TASK_ALREADY_BOOKMARKED, TASK_NOT_FOUND
from app.crud import bookmark as crud_bookmark
from app.crud import task as crud_task
from app.database import get_db
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import TaskRead

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get(
    "", response_model=list[TaskRead], summary="Danh sách task (lọc theo status/priority)"
)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
) -> list[TaskRead]:
    tasks = await crud_task.get_tasks(db, status=status, priority=priority)
    return [TaskRead.model_validate(t) for t in tasks]


@router.post(
    "/{task_id}/bookmark",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Bookmark 1 task",
    responses={
        401: {"description": "Chưa đăng nhập hoặc token không hợp lệ"},
        404: {"description": "Task không tồn tại"},
        409: {"description": "Đã bookmark task này rồi"},
    },
)
async def bookmark_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await crud_task.get_task(db, task_id)
    if task is None:
        raise NotFoundException(TASK_NOT_FOUND)
    if await crud_bookmark.is_bookmarked(db, current_user.id, task_id):
        raise ConflictException(TASK_ALREADY_BOOKMARKED)
    await crud_bookmark.create_bookmark(db, current_user.id, task_id)
