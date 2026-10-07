from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.constants import UNAUTHORIZED_RESPONSE
from app.core.deps import CurrentUser, DbSession, get_current_user
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.messages import EMAIL_ALREADY_EXISTS, INVALID_CREDENTIALS, USER_NOT_FOUND
from app.core.security import create_access_token
from app.crud import user as crud_user
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserProfile, UserUpdate
from app.services import user as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
    responses={409: {"description": "Username hoặc email đã tồn tại"}},
)
async def register(data: UserCreate, db: DbSession) -> UserProfile:
    user = await user_service.register_user(db, data)
    return UserProfile.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Đăng nhập, trả về access token",
    responses={401: {"description": "Sai username hoặc password"}},
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    user = await user_service.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise UnauthorizedException(INVALID_CREDENTIALS)
    token = create_access_token(subject=user.username)
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Thông tin user hiện tại",
    responses=UNAUTHORIZED_RESPONSE,
)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserProfile:
    return UserProfile.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Cập nhật thông tin user hiện tại",
    responses={
        **UNAUTHORIZED_RESPONSE,
        403: {"description": "Tài khoản bị khoá"},
        409: {"description": "Email đã được user khác sử dụng"},
    },
)
async def update_me(
    data: UserUpdate,
    # Tai khoan bi khoa van xem duoc GET /me nhung khong duoc sua thong tin
    current_user: CurrentUser,
    db: DbSession,
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
async def get_user_profile(username: str, db: DbSession) -> UserProfile:
    user = await crud_user.get_user_by_username(db, username)
    if user is None:
        raise NotFoundException(USER_NOT_FOUND)
    return UserProfile.model_validate(user)
