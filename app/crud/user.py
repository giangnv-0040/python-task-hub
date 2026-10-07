from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_users_by_usernames(db: AsyncSession, usernames: list[str]) -> list[User]:
    result = await db.execute(select(User).where(User.username.in_(usernames)))
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    data: UserCreate,
    hashed_password: str,
    # Role khong nam trong UserCreate (R30): chi CLI/seeder truyen role khac MEMBER
    role: UserRole = UserRole.MEMBER,
) -> User:
    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed_password,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
