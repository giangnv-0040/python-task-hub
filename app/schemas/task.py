from datetime import date, datetime

from pydantic import Field, PositiveInt, field_validator

from app.core.constants import MIN_LENGTH_DEFAULT, TASK_TITLE_MAX_LENGTH
from app.models.task import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema
from app.schemas.tag import TagRead


class _DueDateValidator:
    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("due_date khong duoc o qua khu")
        return value


class TaskCreate(BaseSchema, _DueDateValidator):
    title: str = Field(min_length=MIN_LENGTH_DEFAULT, max_length=TASK_TITLE_MAX_LENGTH)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    assignee_id: PositiveInt | None = None
    # created_by: chua co auth o Ngay 3, tam nhan tu body. Se bo field nay va
    # lay tu current_user khi tich hop auth+permission o Ngay 4/5 (xem skill
    # python-review-pr, rule R20).
    created_by: PositiveInt


class TaskUpdate(BaseSchema, _DueDateValidator):
    title: str | None = Field(
        default=None, min_length=MIN_LENGTH_DEFAULT, max_length=TASK_TITLE_MAX_LENGTH
    )
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assignee_id: PositiveInt | None = None


class TaskRead(BaseSchema):
    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    assignee_id: int | None
    created_by: int
    created_at: datetime
    tags: list[TagRead] = []
