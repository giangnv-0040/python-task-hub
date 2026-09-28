from datetime import datetime

from pydantic import Field, PositiveInt

from app.core.constants import MIN_LENGTH_DEFAULT, PROJECT_NAME_MAX_LENGTH
from app.models.project import ProjectStatus
from app.schemas.base import BaseSchema


class ProjectBase(BaseSchema):
    name: str = Field(min_length=MIN_LENGTH_DEFAULT, max_length=PROJECT_NAME_MAX_LENGTH)
    description: str | None = None
    manager_id: PositiveInt | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=MIN_LENGTH_DEFAULT, max_length=PROJECT_NAME_MAX_LENGTH
    )
    description: str | None = None
    manager_id: PositiveInt | None = None
    status: ProjectStatus | None = None


class ProjectRead(ProjectBase):
    id: int
    status: ProjectStatus
    created_at: datetime
