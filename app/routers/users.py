from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.messages import USER_NOT_FOUND
from app.crud import user as crud_user
from app.database import get_db
from app.schemas.user import UserProfile

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get(
    "/{username}/profile",
    response_model=UserProfile,
    summary="Hồ sơ public của user",
    responses={404: {"description": "User không tồn tại"}},
)
async def get_user_profile(
    username: str, db: AsyncSession = Depends(get_db)
) -> UserProfile:
    user = await crud_user.get_user_by_username(db, username)
    if user is None:
        raise NotFoundException(USER_NOT_FOUND)
    return UserProfile.model_validate(user)
