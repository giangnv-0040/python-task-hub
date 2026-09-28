from pydantic import Field

from app.core.constants import MIN_LENGTH_DEFAULT, TAG_COLOR_MAX_LENGTH, TAG_NAME_MAX_LENGTH
from app.schemas.base import BaseSchema


class TagBase(BaseSchema):
    name: str = Field(min_length=MIN_LENGTH_DEFAULT, max_length=TAG_NAME_MAX_LENGTH)
    color: str = Field(min_length=MIN_LENGTH_DEFAULT, max_length=TAG_COLOR_MAX_LENGTH)


class TagCreate(TagBase):
    pass


class TagUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=MIN_LENGTH_DEFAULT, max_length=TAG_NAME_MAX_LENGTH
    )
    color: str | None = Field(
        default=None, min_length=MIN_LENGTH_DEFAULT, max_length=TAG_COLOR_MAX_LENGTH
    )


class TagRead(TagBase):
    id: int
