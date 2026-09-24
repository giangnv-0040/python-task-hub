# TaskHub API — Đặc tả kỹ thuật (bản chốt)

> Dự án có 2 tài liệu gốc xung đột nhau (đặc tả workspace-based `/api/v1` vs lộ trình 8 ngày đơn giản hơn `/api/...`). Đã chốt: **lấy lộ trình 8 ngày làm nguồn chuẩn**. File này là bản spec hợp nhất, dùng để đối chiếu khi code.

## Tech stack
- FastAPI 0.111+
- SQLAlchemy 2.x (async) + asyncpg
- Alembic (migration)
- Pydantic v2
- Redis (caching, Ngày 7)
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

Không có Workspace / multi-tenancy — mọi user đã đăng nhập đều thấy được project/task.

## Roles & Permissions

- **ADMIN**: full quyền trên mọi resource.
- **PM**: full quyền trên các `project` mà `project.manager_id == user.id` (tạo/sửa/xoá task, xoá comment bất kỳ trong project đó).
- **MEMBER**: CRUD task được assign, thêm comment, chỉ sửa/xoá **comment của chính mình**, bookmark task.

## API Endpoints (tổng hợp theo ngày triển khai)

| Ngày | Endpoint |
|---|---|
| 2 | `GET /api/projects`, `GET /api/projects/{id}`, `GET /api/tags` (+ CRUD đầy đủ Project/Tag: POST/PATCH/DELETE) |
| 3 | `GET /api/projects/{id}/tasks`, `POST /api/projects/{id}/tasks`, `GET /api/users/{username}/profile` |
| 4 | `POST /api/users/register`, `POST /api/users/login`, `GET /api/users/me`, `PUT /api/users/me` |
| 5 | `GET /api/tasks?status=&priority=`, `GET /api/projects/{id}/tasks?skip=&limit=`, `POST /api/tasks/{id}/bookmark` |
| 6 | `POST /api/tasks/{id}/assign`, `POST /api/tasks/{id}/comments`, `DELETE /api/tasks/{id}/comments/{comment_id}` |
| 7 | (không thêm endpoint mới — test, background email khi có comment, cache Redis cho `/api/tags`) |
| 8 | (không thêm endpoint mới — CORS, logging, Docker) |

## Ghi chú
- Chi tiết cấu trúc thư mục & lý do thiết kế: xem [PLAN.md](PLAN.md).
- Checklist thực hành từng ngày: xem [TASKS.md](TASKS.md).
