from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.cache import get_redis
from app.core.debug import start_debugpy
from app.core.exceptions import AppException, error_response
from app.core.logging import setup_logging
from app.core.middleware import setup_middlewares
from app.routers import attachments, comments, projects, tags, tasks, users

setup_logging()
start_debugpy()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    # Dong connection pool Redis (cache) khi tat app
    await get_redis().aclose()


app = FastAPI(title="TaskHub API", lifespan=lifespan)

setup_middlewares(app, cors_origins=settings.cors_origins)

app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.project_tasks_router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(attachments.task_attachments_router)
app.include_router(attachments.router)
app.include_router(tags.router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return error_response(exc.status_code, exc.message, exc.headers)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
