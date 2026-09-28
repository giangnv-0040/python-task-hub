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

## Ngày 4 — Xác thực người dùng bằng JWT & OAuth2

- [ ] Hash password với passlib/bcrypt
- [ ] Tạo JWT access token có `expire`
- [ ] Dependency `get_current_user`
- [ ] `POST /api/users/register`
- [ ] `POST /api/users/login`
- [ ] `GET /api/users/me`
- [ ] `PUT /api/users/me`

## Ngày 5 — Phân quyền (Dependencies), Filtering, Pagination

- [ ] Dependency `get_current_active_user`
- [ ] Dependency `verify_admin_role`
- [ ] Dependency `verify_project_manager`
- [ ] Filtering: `GET /api/tasks?status=&priority=`
- [ ] Pagination: `GET /api/projects/{id}/tasks?skip=&limit=`
- [ ] `POST /api/tasks/{task_id}/bookmark` (yêu cầu đã login)

## Ngày 6 — Nghiệp vụ phức tạp & Transaction

- [ ] `POST /api/tasks/{task_id}/assign`
- [ ] `POST /api/tasks/{task_id}/comments`
- [ ] `DELETE /api/tasks/{task_id}/comments/{comment_id}` (chỉ tác giả hoặc Admin/PM)

## Ngày 7 — Testing, Background Tasks & Caching

- [ ] Pytest integration test: luồng đăng ký + tạo task (`TestClient`)
- [ ] Background task: gửi email khi có người comment vào task
- [ ] Cache Redis cho `GET /api/tags`, invalidate khi có thay đổi

## Ngày 8 — Tổng kết, Build hoàn chỉnh

- [ ] CORS: cấu hình `CORSMiddleware`
- [ ] Logging: cấu hình log theo dõi lỗi server
- [ ] `Dockerfile`
- [ ] `docker-compose.yml` (App + PostgreSQL)
- [ ] `docker compose up` chạy được toàn bộ stack
