# TaskHub API — Kế hoạch triển khai 8 ngày

Xây dựng tuần tự từng ngày (tutorial-driven), mỗi ngày kết thúc bằng review + giải thích quyết định thiết kế trước khi qua ngày tiếp theo. Xem checklist chi tiết tại [TASKS.md](TASKS.md), đặc tả tổng hợp tại [SPEC.md](SPEC.md).

## Ngày 1 — Setup môi trường & làm quen FastAPI/SQLAlchemy ✅ Hoàn thành
Cấu trúc thư mục chuẩn (`routers/models/schemas/crud`), kết nối DB async, `.env`, models SQLAlchemy (User/Project/Task/Tag/Comment + bảng trung gian), router rỗng, Alembic + migration đầu tiên.

## Ngày 2 — CRUD cơ bản với SQLAlchemy, Pydantic & APIRouter
Pydantic schemas (Create/Update/Response) cho Project & Tag, CRUD layer, full CRUD endpoints, test qua Swagger UI (`/docs`).

## Ngày 3 — Quan hệ Model & Tối ưu hóa truy vấn
ForeignKey/relationship, many-to-many Task-Tag, eager loading (`joinedload`), nested Pydantic models, endpoint task theo project.

## Ngày 4 — Xác thực người dùng bằng JWT & OAuth2
Hash password (passlib/bcrypt), JWT access token, `get_current_user` dependency, register/login/me.

## Ngày 5 — Phân quyền (Dependencies), Filtering, Pagination
Custom dependencies (`verify_admin_role`, `verify_project_manager`), filter theo status/priority, pagination `skip`/`limit`, bookmark task.

## Ngày 6 — Nghiệp vụ phức tạp & Transaction
Assign task, comment, kiểm soát quyền chặt chẽ (chỉ tác giả comment hoặc Admin/PM được sửa/xoá).

## Ngày 7 — Testing, Background Tasks & Caching
Pytest integration test (đăng ký + tạo task), background task gửi email khi có comment, cache Redis cho danh sách tag.

## Ngày 8 — Tổng kết, Build hoàn chỉnh
CORS, logging, Dockerfile + docker-compose (App + PostgreSQL).

## Quyết định đã chốt
- **Nguồn chuẩn**: lộ trình 8 ngày (không phải đặc tả workspace-based gốc).
- **DB**: PostgreSQL, SQLAlchemy 2.x async, Alembic.
- **Hình thức**: build từng ngày, dừng lại review sau mỗi ngày.
