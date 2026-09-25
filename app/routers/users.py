from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.messages import (
    EMAIL_ALREADY_EXISTS,
    INVALID_CREDENTIALS,
    USER_NOT_FOUND,
    USERNAME_ALREADY_EXISTS,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.crud import user as crud_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserProfile, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=201,
    summary="Đăng ký tài khoản mới",
    responses={409: {"description": "Username hoặc email đã tồn tại"}},
)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserProfile:
    if await crud_user.get_user_by_username(db, data.username) is not None:
        raise ConflictException(USERNAME_ALREADY_EXISTS)
    if await crud_user.get_user_by_email(db, data.email) is not None:
        raise ConflictException(EMAIL_ALREADY_EXISTS)
    user = await crud_user.create_user(db, data, hash_password(data.password))
    return UserProfile.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Đăng nhập, trả về access token",
    responses={401: {"description": "Sai username hoặc password"}},
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await crud_user.get_user_by_username(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedException(INVALID_CREDENTIALS)
    token = create_access_token(subject=user.username)
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Thông tin user hiện tại",
    responses={401: {"description": "Chưa đăng nhập hoặc token không hợp lệ"}},
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfile:
    return UserProfile.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Cập nhật thông tin user hiện tại",
    responses={
        401: {"description": "Chưa đăng nhập hoặc token không hợp lệ"},
        409: {"description": "Email đã được user khác sử dụng"},
    },
)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    if data.email is not None and data.email != current_user.email:
        existing = await crud_user.get_user_by_email(db, data.email)
        if existing is not None:
            raise ConflictException(EMAIL_ALREADY_EXISTS)
    updated = await crud_user.update_user(db, current_user, data)
    return UserProfile.model_validate(updated)


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
