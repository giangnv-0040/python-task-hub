"""Nghiep vu quan tri user (Ngay 8), goi tu CLI `python -m app.cli create-admin`.

API register khong cho chon role (R30) -> admin dau tien chi tao duoc qua day.
"""

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException
from app.core.messages import CLI_USERNAME_TAKEN_BY_NON_ADMIN, EMAIL_ALREADY_EXISTS
from app.core.security import hash_password
from app.crud import user as crud_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


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
    if await crud_user.get_user_by_email(db, data.email) is not None:
        raise ConflictException(EMAIL_ALREADY_EXISTS)
    hashed_password = await run_in_threadpool(hash_password, data.password)
    admin = await crud_user.create_user(db, data, hashed_password, UserRole.ADMIN)
    return admin, True
