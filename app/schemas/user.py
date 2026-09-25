from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    MIN_LENGTH_DEFAULT,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    TOKEN_TYPE_BEARER,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from app.core.messages import FIELD_NOT_NULLABLE
from app.models.user import UserRole
from app.schemas.base import BaseSchema

# User.email la String(255) trong DB; rang buoc max_length khop DB
# ngay ca khi da dung EmailStr de validate dinh dang.
EmailField = Annotated[EmailStr, Field(max_length=EMAIL_MAX_LENGTH)]

# Khong strip password (BaseSchema strip moi string): khoang trang la ky tu hop
# le cua password, va form login (OAuth2PasswordRequestForm) khong strip.
PasswordField = Annotated[
    str,
    StringConstraints(
        strip_whitespace=False,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    ),
]


class UserProfile(BaseSchema):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseSchema):
    username: str = Field(min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)
    email: EmailField
    full_name: str = Field(min_length=MIN_LENGTH_DEFAULT, max_length=FULL_NAME_MAX_LENGTH)
    password: PasswordField


class UserUpdate(BaseSchema):
    email: EmailField | None = None
    full_name: str | None = Field(
        default=None, min_length=MIN_LENGTH_DEFAULT, max_length=FULL_NAME_MAX_LENGTH
    )

    @field_validator("email", "full_name")
    @classmethod
    def not_explicit_null(cls, value: str | None) -> str | None:
        # Bo qua field thi giu nguyen, nhung gui null tuong minh se ghi de
        # cot NOT NULL (exclude_unset van coi null la "da set") -> chan o 422.
        if value is None:
            raise ValueError(FIELD_NOT_NULLABLE)
        return value


class Token(BaseSchema):
    access_token: str
    token_type: str = TOKEN_TYPE_BEARER
