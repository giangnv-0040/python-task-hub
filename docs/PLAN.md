# TaskHub API — Kế hoạch triển khai 8 ngày

Xây dựng tuần tự từng ngày (tutorial-driven), mỗi ngày kết thúc bằng review + giải thích quyết định thiết kế trước khi qua ngày tiếp theo. Xem checklist chi tiết tại [TASKS.md](TASKS.md), đặc tả tổng hợp tại [SPEC.md](SPEC.md).

## Ngày 1 — Setup môi trường & làm quen FastAPI/SQLAlchemy ✅ Hoàn thành
Cấu trúc thư mục chuẩn (`routers/models/schemas/crud`), kết nối DB async, `.env`, models SQLAlchemy (User/Project/Task/Tag/Comment + bảng trung gian), router rỗng, Alembic + migration đầu tiên.

## Ngày 2 — CRUD cơ bản với SQLAlchemy, Pydantic & APIRouter ✅ Hoàn thành
Pydantic schemas (Create/Update/Response) cho Project & Tag, CRUD layer, full CRUD endpoints, test qua Swagger UI (`/docs`).

## Ngày 3 — Quan hệ Model & Tối ưu hóa truy vấn ✅ Hoàn thành
ForeignKey/relationship, many-to-many Task-Tag, eager loading (`joinedload`), nested Pydantic models, endpoint task theo project.

## Ngày 4 — Xác thực người dùng bằng JWT & OAuth2 ✅ Hoàn thành
Hash password (passlib/bcrypt), JWT access token, `get_current_user` dependency, register/login/me.

## Ngày 5 — Phân quyền (Dependencies), Filtering, Pagination ✅ Hoàn thành
Custom dependencies (`verify_admin_role`, `verify_project_manager`), filter theo status/priority, pagination `skip`/`limit`, bookmark task.

## Ngày 6 — Nghiệp vụ phức tạp, Transaction & Xử lý file ✅ Hoàn thành
Assign task, comment, kiểm soát quyền chặt chẽ (chỉ tác giả comment hoặc Admin/PM được sửa/xoá). Đính kèm file cho task: `UploadFile` đọc theo chunk, validate size/type, `StreamingResponse` khi download, interface `StorageBackend` đổi được giữa local và S3 (MinIO). Bổ sung index cho các cột filter/FK còn thiếu.

## Ngày 7 — Testing, Background Jobs (Celery) & Caching ✅ Hoàn thành
Unit test + e2e test với pytest, pytest-asyncio, httpx `AsyncClient` (DB test riêng, override dependency, mock `.delay()`). Celery + Redis gửi email khi có comment/assign (Mailpit khi dev, có retry), Celery Beat chạy job `remind_due_tasks` mỗi sáng. Cache Redis cho `GET /api/v1/tags` (invalidate khi create/update/delete), fail-open nếu Redis lỗi.

## Ngày 8 — Tổng kết, Debug, Seeder & Build hoàn chỉnh
CORS, logging tập trung + middleware log request, debug bằng debugpy (attach từ VSCode vào container), CLI seeder bằng Typer, Dockerfile + docker-compose (App + PostgreSQL + Redis + Celery worker/beat + Mailpit + MinIO).

## Quyết định đã chốt
- **Nguồn chuẩn**: lộ trình 8 ngày (không phải đặc tả workspace-based gốc).
- **DB**: PostgreSQL, SQLAlchemy 2.x async, Alembic.
- **Background job**: Celery + Redis (không dùng ARQ); lập lịch bằng Celery Beat.
- **Xử lý file**: gộp vào Ngày 6 (không tách ngày riêng).
- **Hình thức**: build từng ngày, dừng lại review sau mỗi ngày.
