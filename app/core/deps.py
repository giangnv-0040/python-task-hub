from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.messages import INVALID_TOKEN
from app.core.security import decode_access_token
from app.crud import user as crud_user
from app.database import get_db
from app.models.user import User

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
