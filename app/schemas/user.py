from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
