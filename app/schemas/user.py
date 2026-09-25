from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole

# User.email la String(255) trong DB; rang buoc max_length khop DB
# ngay ca khi da dung EmailStr de validate dinh dang.
EmailField = Annotated[EmailStr, Field(max_length=255)]


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailField
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: EmailField | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
