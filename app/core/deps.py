from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.messages import (
    ACCOUNT_INACTIVE,
    INVALID_TOKEN,
    PERMISSION_DENIED,
    PROJECT_NOT_FOUND,
)
from app.core.security import decode_access_token
from app.crud import project as crud_project
from app.crud import user as crud_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login", auto_error=False)


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


async def verify_project_manager(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    project = await crud_project.get_project(db, project_id)
    if project is None:
        raise NotFoundException(PROJECT_NOT_FOUND)
    if current_user.role == UserRole.ADMIN:
        return project
    if current_user.role == UserRole.PM and project.manager_id == current_user.id:
        return project
    raise ForbiddenException(PERMISSION_DENIED)
