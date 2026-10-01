"""Nghiep vu user: dang ky, dang nhap.

bcrypt co tinh cham (~0.2s) va chiem CPU -> moi lan hash/verify chay trong
threadpool, khong chan event loop (R26).
"""

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException
from app.core.messages import EMAIL_ALREADY_EXISTS, USERNAME_ALREADY_EXISTS
from app.core.security import hash_password, verify_password
from app.crud import user as crud_user
from app.models.user import User
from app.schemas.user import UserCreate


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    if await crud_user.get_user_by_username(db, data.username) is not None:
        raise ConflictException(USERNAME_ALREADY_EXISTS)
    if await crud_user.get_user_by_email(db, data.email) is not None:
        raise ConflictException(EMAIL_ALREADY_EXISTS)
    hashed_password = await run_in_threadpool(hash_password, data.password)
    return await crud_user.create_user(db, data, hashed_password)


async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
    """Tra ve user neu dung username/password, nguoc lai None."""
    user = await crud_user.get_user_by_username(db, username)
    if user is None:
        return None
    if not await run_in_threadpool(verify_password, password, user.hashed_password):
        return None
    return user
