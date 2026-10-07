"""Nghiep vu user: dang ky, dang nhap (API) va tao admin (CLI `create-admin`).

API register khong cho chon role (R30) -> admin dau tien chi tao duoc qua CLI.
bcrypt co tinh cham (~0.2s) va chiem CPU -> moi lan hash/verify chay trong
threadpool, khong chan event loop (R26).
"""

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException
from app.core.messages import (
    CLI_USERNAME_TAKEN_BY_NON_ADMIN,
    EMAIL_ALREADY_EXISTS,
    USERNAME_ALREADY_EXISTS,
)
from app.core.security import hash_password, verify_password
from app.crud import user as crud_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


async def _create_user(db: AsyncSession, data: UserCreate, role: UserRole) -> User:
    """Tao user sau khi da check username; dung chung cho register va create-admin."""
    if await crud_user.get_user_by_email(db, data.email) is not None:
        raise ConflictException(EMAIL_ALREADY_EXISTS)
    hashed_password = await run_in_threadpool(hash_password, data.password)
    return await crud_user.create_user(db, data, hashed_password, role)


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    if await crud_user.get_user_by_username(db, data.username) is not None:
        raise ConflictException(USERNAME_ALREADY_EXISTS)
    return await _create_user(db, data, UserRole.MEMBER)


async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
    """Tra ve user neu dung username/password, nguoc lai None."""
    user = await crud_user.get_user_by_username(db, username)
    if user is None:
        return None
    if not await run_in_threadpool(verify_password, password, user.hashed_password):
        return None
    return user


async def create_admin(db: AsyncSession, data: UserCreate) -> tuple[User, bool]:
    """Tra ve (admin, created). Chay lai voi username cua admin da co thi khong
    lam gi (created=False, khong doi password); username/email dang thuoc user
    khong phai admin thi bao loi, khong tu nang quyen."""
    existing = await crud_user.get_user_by_username(db, data.username)
    if existing is not None:
        if existing.role != UserRole.ADMIN:
            raise ConflictException(
                CLI_USERNAME_TAKEN_BY_NON_ADMIN.format(username=data.username)
            )
        return existing, False
    return await _create_user(db, data, UserRole.ADMIN), True
