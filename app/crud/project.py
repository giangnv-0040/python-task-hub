from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagination, paginate
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    return await db.get(Project, project_id)


async def get_project_by_name(db: AsyncSession, name: str) -> Project | None:
    # projects.name khong unique -> lay ban ghi dau tien theo id cho on dinh
    result = await db.execute(
        select(Project).where(Project.name == name).order_by(Project.id).limit(1)
    )
    return result.scalar_one_or_none()


async def get_projects(
    db: AsyncSession, pagination: Pagination
) -> tuple[list[Project], int]:
    return await paginate(db, select(Project).order_by(Project.id), pagination)


async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession, project: Project, data: ProjectUpdate
) -> Project:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()
