from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel

from app.core.constants import DEFAULT_LIMIT, DEFAULT_SKIP, MAX_LIMIT


class Pagination(BaseModel):
    skip: int
    limit: int


def pagination_params(
    skip: int = Query(default=DEFAULT_SKIP, ge=0),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> Pagination:
    return Pagination(skip=skip, limit=limit)


PaginationDep = Annotated[Pagination, Depends(pagination_params)]
