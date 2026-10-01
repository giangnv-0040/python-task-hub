from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.cache import get_redis
from app.core.exceptions import AppException
from app.routers import attachments, comments, projects, tags, tasks, users


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    # Dong connection pool Redis (cache) khi tat app
    await get_redis().aclose()


app = FastAPI(title="TaskHub API", lifespan=lifespan)

api_router = APIRouter(prefix=settings.api_prefix)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.project_tasks_router)
api_router.include_router(tasks.router)
api_router.include_router(comments.router)
api_router.include_router(attachments.task_attachments_router)
api_router.include_router(attachments.router)
api_router.include_router(tags.router)

app.include_router(api_router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.message}},
        headers=exc.headers,
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
