from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.messages import PROJECT_NOT_FOUND
from app.crud import project as crud_project
from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def get_project_detail(
    project_id: int, db: AsyncSession = Depends(get_db)
) -> Project:
    project = await crud_project.get_project(db, project_id)
    if project is None:
        raise NotFoundException(PROJECT_NOT_FOUND)
    return project


@router.get("", response_model=list[ProjectRead], summary="Danh sách project")
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[ProjectRead]:
    projects = await crud_project.get_projects(db)
    return [ProjectRead.model_validate(p) for p in projects]


@router.get(
    "/{project_id}", response_model=ProjectRead, summary="Chi tiết 1 project"
)
async def get_project(
    project: Project = Depends(get_project_detail),
) -> ProjectRead:
    return ProjectRead.model_validate(project)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo project mới",
)
async def create_project(
    data: ProjectCreate, db: AsyncSession = Depends(get_db)
) -> ProjectRead:
    project = await crud_project.create_project(db, data)
    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}", response_model=ProjectRead, summary="Cập nhật project"
)
async def update_project(
    data: ProjectUpdate,
    project: Project = Depends(get_project_detail),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    updated = await crud_project.update_project(db, project, data)
    return ProjectRead.model_validate(updated)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá project",
)
async def delete_project(
    project: Project = Depends(get_project_detail),
    db: AsyncSession = Depends(get_db),
) -> None:
    await crud_project.delete_project(db, project)
