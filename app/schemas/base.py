from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)


class Page(BaseSchema, Generic[T]):
    """Response chuan cho endpoint list co pagination (R37): tra ca `total` de
    client biet con trang nao, khong chi tra list phang."""

    items: list[T]
    total: int
