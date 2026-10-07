from typing import Annotated, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_LIMIT, DEFAULT_SKIP, MAX_LIMIT

T = TypeVar("T")


class Pagination(BaseModel):
    skip: int
    limit: int


def pagination_params(
    skip: Annotated[int, Query(ge=0)] = DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> Pagination:
    return Pagination(skip=skip, limit=limit)


PaginationDep = Annotated[Pagination, Depends(pagination_params)]


async def paginate(
    db: AsyncSession, query: Select[tuple[T]], pagination: Pagination
) -> tuple[list[T], int]:
    """Chay `query` theo trang, tra kem tong so ban ghi khop dieu kien (R37).

    `query` phai co `order_by` ket thuc bang `id` de cac trang on dinh.
    """
    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    items = await db.scalars(query.offset(pagination.skip).limit(pagination.limit))
    return list(items.all()), total or 0
