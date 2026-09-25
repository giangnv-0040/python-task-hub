from datetime import datetime

from app.models.user import UserRole
from app.schemas.base import BaseSchema


class UserProfile(BaseSchema):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
