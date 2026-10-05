# TaskHub API — Đặc tả kỹ thuật (bản chốt)

> Dự án có 2 tài liệu gốc xung đột nhau (đặc tả workspace-based `/api/v1` vs lộ trình 8 ngày đơn giản hơn `/api/...`). Đã chốt: **lấy lộ trình 8 ngày làm nguồn chuẩn**. Mọi endpoint đặt dưới prefix có version `/api/v1` (cấu hình qua env `API_PREFIX`). File này là bản spec hợp nhất, dùng để đối chiếu khi code.

## Tech stack
- FastAPI 0.111+
- SQLAlchemy 2.x (async) + asyncpg
- Alembic (migration)
- Pydantic v2
- Redis (cache `/api/v1/tags` + broker/result backend cho Celery, Ngày 7)
- Celery (worker gửi email) + Celery Beat (job định kỳ) — Ngày 7
- Lưu trữ file: local disk (mặc định) / S3 qua `aioboto3` (MinIO khi dev) — Ngày 6
- pytest + pytest-asyncio + httpx `AsyncClient` (unit test + e2e test) — Ngày 7
- `logging` chuẩn Python + debugpy (debug remote trong Docker) — Ngày 8
- Typer (CLI seeder / quản trị) — Ngày 8
- PostgreSQL 16
- Docker / docker-compose (Ngày 8)

## DB Schema (entities)

| Bảng | Cột chính |
|---|---|
| `users` | id, username, email, full_name, hashed_password, role (`ADMIN`/`PM`/`MEMBER`), is_active, created_at |
| `projects` | id, name, description, manager_id (FK→users), status (`ACTIVE`/`ARCHIVED`), created_at |
| `tasks` | id, project_id (FK), title, description, status (`TODO`/`IN_PROGRESS`/`IN_REVIEW`/`DONE`), priority (`LOW`/`MEDIUM`/`HIGH`/`URGENT`), due_date, assignee_id (FK→users), created_by (FK→users), created_at |
| `tags` | id, name, color |
| `task_tags` | task_id, tag_id (M2M, bảng trung gian thuần) |
| `comments` | id, task_id (FK), author_id (FK→users), content, created_at |
| `bookmarks` | user_id, task_id (M2M, bảng trung gian thuần) |
| `attachments` | id, task_id (FK), uploaded_by (FK→users), filename (tên gốc), storage_key (đường dẫn local / S3 key), content_type, size, created_at |

### Index (tối ưu truy vấn)
- Đã có: index FK `tasks.project_id`, `tasks.assignee_id`, `tasks.created_by`; unique index `users.username`, `users.email`.
- Bổ sung Ngày 6: `comments.task_id`, `comments.author_id`, `attachments.task_id`, composite `tasks(status, priority)` phục vụ filter `GET /api/v1/tasks`.

Không có Workspace / multi-tenancy — mọi user đã đăng nhập đều thấy được project/task.

## Roles & Permissions

- **ADMIN**: full quyền trên mọi resource.
- **PM**: full quyền trên các `project` mà `project.manager_id == user.id` (tạo/sửa/xoá task, xoá comment bất kỳ trong project đó).
- **MEMBER**: CRUD task được assign, thêm comment, chỉ sửa/xoá **comment của chính mình**, bookmark task, upload/xoá **attachment của chính mình**.

## API Endpoints (tổng hợp theo ngày triển khai)

| Ngày | Endpoint |
|---|---|
| 2 | `GET /api/v1/projects`, `GET /api/v1/projects/{id}`, `GET /api/v1/tags` (+ CRUD đầy đủ Project/Tag: POST/PATCH/DELETE) |
| 3 | `GET /api/v1/projects/{id}/tasks`, `POST /api/v1/projects/{id}/tasks`, `GET /api/v1/users/{username}/profile` |
| 4 | `POST /api/v1/users/register`, `POST /api/v1/users/login`, `GET /api/v1/users/me`, `PUT /api/v1/users/me` |
| 5 | `GET /api/v1/tasks?status=&priority=`, `GET /api/v1/projects/{id}/tasks?skip=&limit=`, `POST /api/v1/tasks/{id}/bookmark` |
| 6 | `POST /api/v1/tasks/{id}/assign`, `POST /api/v1/tasks/{id}/comments`, `DELETE /api/v1/tasks/{id}/comments/{comment_id}`, `POST /api/v1/tasks/{id}/attachments`, `GET /api/v1/tasks/{id}/attachments`, `GET /api/v1/attachments/{id}/download`, `DELETE /api/v1/attachments/{id}` |
| 7 | (không thêm endpoint mới — unit/e2e test, Celery gửi email khi có comment/assign, Celery Beat nhắc task sắp đến hạn, cache Redis cho `/api/v1/tags`) |
| 8 | (không thêm endpoint mới — CORS, logging, debugpy, CLI seeder bằng Typer, Docker) |

## Quy ước kỹ thuật

### Xử lý file (Ngày 6)
- Upload qua `UploadFile`, đọc theo chunk (không `await file.read()` cả file vào RAM), giới hạn size (`MAX_UPLOAD_SIZE`) và whitelist `content_type`.
- Interface `StorageBackend` với 2 implementation `LocalStorage` / `S3Storage`, chọn qua biến `STORAGE_BACKEND=local|s3`.
- Download trả `StreamingResponse` (có `Content-Disposition`), không load toàn bộ file vào bộ nhớ.
- `storage_key` sinh bằng UUID — không dùng tên file người dùng làm đường dẫn (tránh path traversal / ghi đè).

### Email & lập lịch (Ngày 7)
- Celery app (`app/worker/celery_app.py`), broker + result backend là Redis.
- Task `send_comment_notification` (gửi assignee khi có comment mới) và `send_assign_notification` (gửi khi được assign); router chỉ gọi `.delay()` sau khi commit DB thành công.
- Celery Beat: job `remind_due_tasks` chạy mỗi sáng, gửi mail nhắc các task chưa `DONE` có `due_date` trong 24h tới.
- SMTP khi dev dùng Mailpit (docker-compose); cấu hình `SMTP_HOST/PORT/USER/PASSWORD` qua `.env`.
- Có retry (`autoretry_for`, `max_retries`) khi SMTP lỗi.

### Testing (Ngày 7)
- `pytest` + `pytest-asyncio`, client là `httpx.AsyncClient(transport=ASGITransport(app=app))`.
- DB test riêng (`TEST_DATABASE_URL`); `conftest.py` tạo/drop schema, override dependency `get_db`; Celery chạy `task_always_eager` hoặc mock `.delay()`.
- Unit test: `core/security` (hash/verify, JWT), `crud/*`, dependency phân quyền.
- E2E test: register → login → tạo project/task → comment → upload/download file; các case 401/403/404, filter + pagination.

### Performance
- Mọi I/O trong `async def` phải là async (asyncpg, aioboto3, aiofiles); tác vụ blocking (bcrypt, SMTP) chạy qua `run_in_threadpool` hoặc đẩy sang Celery.
- Tránh N+1: dùng `selectinload`/`joinedload` cho các quan hệ trả về trong response.
- Mọi endpoint list đều có pagination (`skip`/`limit`, `limit` có giới hạn tối đa).

### Logging & Debug (Ngày 8)
- Cấu hình `logging` tập trung (`app/core/logging.py`): format có timestamp/level/logger, level lấy từ `LOG_LEVEL`.
- Middleware log request (method, path, status, thời gian xử lý); exception handler log stacktrace lỗi 500.
- debugpy: bật bằng `DEBUGPY=1`, listen `0.0.0.0:5678`, expose port trong docker-compose, kèm `.vscode/launch.json` để attach.

### CLI Seeder (Ngày 8)
- Typer app `app/cli.py`, chạy `python -m app.cli <command>`.
- Lệnh: `seed` (tuỳ chọn `--users`, `--projects`, `--tasks-per-project`), `create-admin`, `reset-db`.
- Seeder idempotent (chạy lại không tạo trùng), dùng lại CRUD layer / async session.

## Ghi chú
- Chi tiết cấu trúc thư mục & lý do thiết kế: xem [PLAN.md](PLAN.md).
- Checklist thực hành từng ngày: xem [TASKS.md](TASKS.md).
