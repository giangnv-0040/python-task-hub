from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel

from app.core.constants import DEFAULT_LIMIT, DEFAULT_SKIP, MAX_LIMIT


class Pagination(BaseModel):
    skip: int
    limit: int


def pagination_params(
    skip: Annotated[int, Query(ge=0)] = DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> Pagination:
    return Pagination(skip=skip, limit=limit)


PaginationDep = Annotated[Pagination, Depends(pagination_params)]
