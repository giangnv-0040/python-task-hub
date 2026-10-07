from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ADMIN_ONLY_RESPONSES,
    MANAGER_NOT_FOUND_RESPONSE,
    PROJECT_MANAGER_NOT_FOUND_RESPONSE,
    PERMISSION_RESPONSES,
    PROJECT_NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.core.deps import (
    DbSession,
    get_current_active_user,
    get_project_detail,
    verify_admin_role,
    verify_project_manager,
)
from app.core.exceptions import NotFoundException
from app.core.messages import MANAGER_NOT_FOUND
from app.core.pagination import PaginationDep
from app.crud import project as crud_project
from app.crud import user as crud_user
from app.models.project import Project
from app.models.user import UserRole
from app.schemas.base import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

ManagedProjectDep = Annotated[Project, Depends(verify_project_manager)]

async def _ensure_valid_manager(db: AsyncSession, manager_id: int | None) -> None:
    # manager_id quyet dinh ai duoc quan ly project (verify_project_manager), nen
    # phai la PM dang hoat dong; id khong ton tai con gay loi FK (500) o DB.
    if manager_id is None:
        return
    manager = await crud_user.get_user(db, manager_id)
    if manager is None or not manager.is_active or manager.role != UserRole.PM:
        raise NotFoundException(MANAGER_NOT_FOUND)


@router.get(
    "",
    response_model=Page[ProjectRead],
    summary="Danh sách project (phân trang)",
    responses=UNAUTHORIZED_RESPONSE,
    dependencies=[Depends(get_current_active_user)],
)
async def list_projects(pagination: PaginationDep, db: DbSession) -> Page[ProjectRead]:
    projects, total = await crud_project.get_projects(db, pagination)
    return Page(items=[ProjectRead.model_validate(p) for p in projects], total=total)


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Chi tiết 1 project",
    responses={**UNAUTHORIZED_RESPONSE, **PROJECT_NOT_FOUND_RESPONSE},
    dependencies=[Depends(get_current_active_user)],
)
async def get_project(
    project: Annotated[Project, Depends(get_project_detail)],
) -> ProjectRead:
    return ProjectRead.model_validate(project)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo project mới (chỉ Admin)",
    responses={
        **ADMIN_ONLY_RESPONSES,
        **MANAGER_NOT_FOUND_RESPONSE,
    },
    dependencies=[Depends(verify_admin_role)],
)
async def create_project(data: ProjectCreate, db: DbSession) -> ProjectRead:
    await _ensure_valid_manager(db, data.manager_id)
    project = await crud_project.create_project(db, data)
    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Cập nhật project",
    responses={**PROJECT_MANAGER_NOT_FOUND_RESPONSE, **PERMISSION_RESPONSES},
)
async def update_project(
    data: ProjectUpdate,
    project: ManagedProjectDep,
    db: DbSession,
) -> ProjectRead:
    await _ensure_valid_manager(db, data.manager_id)
    updated = await crud_project.update_project(db, project, data)
    return ProjectRead.model_validate(updated)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá project",
    responses={**PROJECT_NOT_FOUND_RESPONSE, **PERMISSION_RESPONSES},
)
async def delete_project(project: ManagedProjectDep, db: DbSession) -> None:
    await crud_project.delete_project(db, project)
