from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.constants import TASK_NOT_FOUND_RESPONSE, UNAUTHORIZED_RESPONSE
from app.core.deps import CurrentUser, DbSession, TaskDetailDep, verify_comment_owner_or_manager
from app.crud import comment as crud_comment
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentRead

# Route thao tac tren Comment, chi nested URL duoi /tasks -> dat o comments.py (R18)
router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


@router.post(
    "",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm comment vào task",
    responses={**UNAUTHORIZED_RESPONSE, **TASK_NOT_FOUND_RESPONSE},
)
async def create_comment(
    data: CommentCreate,
    current_user: CurrentUser,
    task: TaskDetailDep,
    db: DbSession,
) -> CommentRead:
    comment = await crud_comment.create_comment(
        db, task.id, data, author_id=current_user.id
    )
    return CommentRead.model_validate(comment)


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá comment (tác giả, PM của project hoặc Admin)",
    responses={
        **UNAUTHORIZED_RESPONSE,
        403: {"description": "Không phải tác giả comment, PM của project hoặc Admin"},
        404: {"description": "Task hoặc comment không tồn tại"},
    },
)
async def delete_comment(
    comment: Annotated[Comment, Depends(verify_comment_owner_or_manager)],
    db: DbSession,
) -> None:
    await crud_comment.delete_comment(db, comment)
