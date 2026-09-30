# TaskHub API — Task List

Tick `[x]` khi làm xong. Xem bối cảnh từng ngày tại [PLAN.md](PLAN.md), spec tại [SPEC.md](SPEC.md).

## Ngày 1 — Setup môi trường & FastAPI/SQLAlchemy ✅

- [x] Cấu trúc thư mục chuẩn: `routers`, `models`, `schemas`, `crud`, `database.py`
- [x] Cài đặt `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `python-dotenv`, `pydantic-settings`
- [x] `database.py`: async engine + session factory + `Base`
- [x] `.env` + `.env.example` chứa config nhạy cảm
- [x] Cấu hình Alembic (async template)
- [x] Models: `User`, `Project`, `Task`, `Tag`, `Comment` + bảng trung gian `task_tags`, `bookmarks`
- [x] `APIRouter` cho `/api/users`, `/api/projects`, `/api/tasks`, `/api/tags`
- [x] `main.py` khởi tạo app, include router
- [x] Migration đầu tiên (`alembic revision --autogenerate` + `upgrade head`), verify bằng Postgres Docker tạm

## Ngày 2 — CRUD cơ bản với SQLAlchemy, Pydantic & APIRouter ✅

- [x] Pydantic schemas cho Project (Create/Update/Response)
- [x] Pydantic schemas cho Tag (Create/Update/Response)
- [x] CRUD layer (`crud/project.py`, `crud/tag.py`)
- [x] `GET /api/projects`
- [x] `GET /api/projects/{project_id}`
- [x] `POST /api/projects`, `PATCH /api/projects/{id}`, `DELETE /api/projects/{id}`
- [x] `GET /api/tags`, `POST /api/tags`, `PATCH /api/tags/{id}`, `DELETE /api/tags/{id}`
- [x] Test qua Swagger UI (`/docs`) — verify bằng curl end-to-end (create/list/get/update/delete + 404)

## Ngày 3 — Quan hệ Model & Tối ưu hóa truy vấn ✅

- [x] ForeignKey/relationship đầy đủ giữa các model (Project↔Task, Task→assignee/creator, Task↔Tag)
- [x] Many-to-many Task-Tag qua `joinedload`
- [x] Nested Pydantic models (`TaskRead.tags: list[TagRead]`)
- [x] `GET /api/projects/{project_id}/tasks`
- [x] `POST /api/projects/{project_id}/tasks`
- [x] `GET /api/users/{username}/profile`

## Ngày 4 — Xác thực người dùng bằng JWT & OAuth2 ✅

- [x] Hash password với passlib/bcrypt
- [x] Tạo JWT access token có `expire`
- [x] Dependency `get_current_user`
- [x] `POST /api/users/register`
- [x] `POST /api/users/login`
- [x] `GET /api/users/me`
- [x] `PUT /api/users/me`

## Ngày 5 — Phân quyền (Dependencies), Filtering, Pagination ✅

- [x] Dependency `get_current_active_user`
- [x] Dependency `verify_admin_role`
- [x] Dependency `verify_project_manager`
- [x] Filtering: `GET /api/tasks?status=&priority=&skip=&limit=`
- [x] Pagination: `GET /api/projects/{id}/tasks?skip=&limit=` (dependency `PaginationDep` dùng chung)
- [x] `POST /api/tasks/{task_id}/bookmark` (yêu cầu đã login, chặn bookmark trùng)

## Ngày 6 — Nghiệp vụ phức tạp, Transaction & Xử lý file

- [ ] `POST /api/tasks/{task_id}/assign`
- [ ] `POST /api/tasks/{task_id}/comments`
- [ ] `DELETE /api/tasks/{task_id}/comments/{comment_id}` (chỉ tác giả hoặc Admin/PM)
- [ ] Migration index: `comments.task_id`, `comments.author_id`, composite `tasks(status, priority)`
- [ ] Model `Attachment` + migration (có index `attachments.task_id`)
- [ ] Interface `StorageBackend` + `LocalStorage` + `S3Storage` (aioboto3), chọn qua `STORAGE_BACKEND`
- [ ] `POST /api/tasks/{task_id}/attachments` (`UploadFile`, đọc theo chunk, giới hạn size, whitelist content type, `storage_key` = UUID)
- [ ] `GET /api/tasks/{task_id}/attachments` (có pagination)
- [ ] `GET /api/attachments/{attachment_id}/download` (`StreamingResponse` + `Content-Disposition`)
- [ ] `DELETE /api/attachments/{attachment_id}` (người upload hoặc Admin/PM; xoá cả file trên storage)

## Ngày 7 — Testing, Background Jobs (Celery) & Caching

- [ ] Cài `pytest`, `pytest-asyncio`, `httpx`; cấu hình `asyncio_mode` trong `pytest.ini`/`pyproject.toml`
- [ ] `tests/conftest.py`: DB test riêng, tạo/drop schema, override `get_db`, fixture `AsyncClient` + user/token
- [ ] Unit test: `core/security` (hash/verify password, tạo/giải mã JWT)
- [ ] Unit test: `crud/*` và dependency phân quyền (`verify_admin_role`, `verify_project_manager`)
- [ ] E2E test: register → login → tạo project/task → comment → upload/download file
- [ ] E2E test: case lỗi 401/403/404, filter + pagination `GET /api/tasks`
- [ ] Celery app (`app/worker/celery_app.py`) với Redis broker/backend
- [ ] Celery task `send_comment_notification` + `send_assign_notification` (có retry), gọi `.delay()` sau commit
- [ ] Celery Beat: job `remind_due_tasks` nhắc task sắp đến hạn (24h) mỗi sáng
- [ ] Test Celery task (chạy eager / mock `.delay()`), kiểm tra mail qua Mailpit
- [ ] Cache Redis cho `GET /api/tags`, invalidate khi có thay đổi

## Ngày 8 — Tổng kết, Debug, Seeder & Build hoàn chỉnh

- [ ] CORS: cấu hình `CORSMiddleware`
- [ ] Logging: `app/core/logging.py` (format, `LOG_LEVEL` từ env), dùng `logging.getLogger(__name__)` trong code
- [ ] Middleware log request (method, path, status, thời gian xử lý) + exception handler log lỗi 500
- [ ] debugpy: bật qua `DEBUGPY=1`, expose port `5678`, thêm `.vscode/launch.json` để attach
- [ ] CLI Typer `app/cli.py`: lệnh `seed` (`--users`, `--projects`, `--tasks-per-project`), `create-admin`, `reset-db`
- [ ] Seeder idempotent (chạy lại không tạo trùng)
- [ ] `Dockerfile`
- [ ] `docker-compose.yml` (App + PostgreSQL + Redis + Celery worker + Celery beat + Mailpit + MinIO)
- [ ] `docker compose up` chạy được toàn bộ stack
