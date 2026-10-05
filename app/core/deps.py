from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.messages import (
    ACCOUNT_INACTIVE,
    ATTACHMENT_NOT_FOUND,
    COMMENT_NOT_FOUND,
    INVALID_TOKEN,
    PERMISSION_DENIED,
    PROJECT_NOT_FOUND,
    TASK_NOT_FOUND,
)
from app.core.security import decode_access_token
from app.crud import attachment as crud_attachment
from app.crud import comment as crud_comment
from app.crud import project as crud_project
from app.crud import task as crud_task
from app.crud import user as crud_user
from app.database import get_db
from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/users/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    if token is None:
        raise UnauthorizedException(INVALID_TOKEN)
    username = decode_access_token(token)
    if username is None:
        raise UnauthorizedException(INVALID_TOKEN)
    user = await crud_user.get_user_by_username(db, username)
    if user is None:
        raise UnauthorizedException(INVALID_TOKEN)
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise ForbiddenException(ACCOUNT_INACTIVE)
    return current_user


async def verify_admin_role(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException(PERMISSION_DENIED)
    return current_user


async def get_project_detail(
    project_id: int, db: AsyncSession = Depends(get_db)
) -> Project:
    project = await crud_project.get_project(db, project_id)
    if project is None:
        raise NotFoundException(PROJECT_NOT_FOUND)
    return project


def can_manage_project(user: User, project: Project | None) -> bool:
    """ADMIN quan ly moi project; PM chi quan ly project minh la manager."""
    if user.role == UserRole.ADMIN:
        return True
    return (
        project is not None
        and user.role == UserRole.PM
        and project.manager_id == user.id
    )


# Cac dependency duoi day khai current_user TRUOC resource: FastAPI resolve theo
# thu tu tham so, nen request chua dang nhap nhan 401 thay vi 404 (khong lo
# resource nao ton tai cho nguoi chua xac thuc).
async def verify_project_manager(
    current_user: User = Depends(get_current_active_user),
    project: Project = Depends(get_project_detail),
) -> Project:
    if not can_manage_project(current_user, project):
        raise ForbiddenException(PERMISSION_DENIED)
    return project


async def get_task_detail(task_id: int, db: AsyncSession = Depends(get_db)) -> Task:
    task = await crud_task.get_task(db, task_id)
    if task is None:
        raise NotFoundException(TASK_NOT_FOUND)
    return task


# Alias Annotated dung chung (R24), dat sau cac dependency ma chung phu thuoc
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
TaskDetailDep = Annotated[Task, Depends(get_task_detail)]


async def verify_task_manager(
    current_user: CurrentUser,
    task: TaskDetailDep,
    db: DbSession,
) -> Task:
    project = await crud_project.get_project(db, task.project_id)
    if not can_manage_project(current_user, project):
        raise ForbiddenException(PERMISSION_DENIED)
    return task


async def _ensure_owner_or_project_manager(
    db: AsyncSession, user: User, owner_id: int, project_id: int
) -> None:
    """Check quyen cap object (BP20) dung chung cho comment/attachment (R14):
    chu so huu, hoac ADMIN / PM cua project chua resource."""
    if owner_id == user.id:
        return
    project = await crud_project.get_project(db, project_id)
    if not can_manage_project(user, project):
        raise ForbiddenException(PERMISSION_DENIED)


async def verify_comment_owner_or_manager(
    comment_id: int,
    current_user: CurrentUser,
    task: TaskDetailDep,
    db: DbSession,
) -> Comment:
    comment = await crud_comment.get_task_comment(db, task.id, comment_id)
    if comment is None:
        raise NotFoundException(COMMENT_NOT_FOUND)
    await _ensure_owner_or_project_manager(
        db, current_user, comment.author_id, task.project_id
    )
    return comment


async def get_attachment_detail(
    attachment_id: int, db: DbSession
) -> Attachment:
    attachment = await crud_attachment.get_attachment(db, attachment_id)
    if attachment is None:
        raise NotFoundException(ATTACHMENT_NOT_FOUND)
    return attachment


AttachmentDetailDep = Annotated[Attachment, Depends(get_attachment_detail)]


async def verify_attachment_owner_or_manager(
    current_user: CurrentUser,
    attachment: AttachmentDetailDep,
    db: DbSession,
) -> Attachment:
    task = await crud_task.get_task(db, attachment.task_id)
    if task is None:
        # Khong xay ra khi FK dung (ondelete=CASCADE), phong truong hop du lieu lech
        raise NotFoundException(ATTACHMENT_NOT_FOUND)
    await _ensure_owner_or_project_manager(
        db, current_user, attachment.uploaded_by, task.project_id
    )
    return attachment
