from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.routers import attachments, comments, projects, tags, tasks, users

app = FastAPI(title="TaskHub API")

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
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.message}},
        headers=exc.headers,
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
