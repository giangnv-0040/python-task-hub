# TaskHub API

Task Management API xây dựng bằng FastAPI, theo lộ trình tutorial-driven 8 ngày (xây dần 1 sample app từ skeleton đến production-ready).

- Đặc tả kỹ thuật (entities, roles, endpoint): [docs/SPEC.md](docs/SPEC.md)
- Kế hoạch 8 ngày: [docs/PLAN.md](docs/PLAN.md)
- Checklist tiến độ: [docs/TASKS.md](docs/TASKS.md)

## Tech stack

FastAPI · SQLAlchemy 2.x (async) · Alembic · Pydantic v2 · PostgreSQL 16 · Redis · Celery · Typer · Docker

## Yêu cầu môi trường

- Python 3.12+
- Docker Desktop (chạy PostgreSQL, và Redis từ Ngày 7)

## Setup lần đầu

Mở terminal (VS Code Terminal hoặc PowerShell bất kỳ) tại thư mục dự án.

**1. Tạo virtual environment và cài dependencies:**
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**2. Tạo file cấu hình:**
```powershell
copy .env.example .env
```
Sửa `.env` nếu cần (mặc định đã khớp với container Postgres ở bước 3).

**3. Bật PostgreSQL (chạy 1 lần, container sẽ tồn tại lâu dài):**
```powershell
docker run -d --name taskhub-postgres -e POSTGRES_USER=taskhub -e POSTGRES_PASSWORD=taskhub -e POSTGRES_DB=taskhub -p 5432:5432 postgres:16
```

**4. Áp dụng migration:**
```powershell
.venv\Scripts\python.exe -m alembic upgrade head
```

**5. Chạy server:**
```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

> macOS/Linux: thay `.venv\Scripts\python.exe` bằng `.venv/bin/python`.

## Chạy lại các lần sau (đã setup xong)

```powershell
docker start taskhub-postgres
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Ngày 7: Redis, Celery, Mailpit

**1. Bật Redis (broker/backend Celery + cache `/api/tags`) và Mailpit (SMTP giả lập khi dev):**
```powershell
docker run -d --name taskhub-redis -p 6379:6379 redis:7-alpine
docker run -d --name taskhub-mailpit -e MP_SMTP_DISABLE_RDNS=true -p 1025:1025 -p 8025:8025 axllent/mailpit
```
Xem mail đã gửi tại http://127.0.0.1:8025.
> `MP_SMTP_DISABLE_RDNS=true`: tắt reverse-DNS IP client, nếu không mỗi lần gửi mail từ host vào container Mailpit chờ ~10s.

**2. Chạy Celery worker (xử lý `send_comment_notification`, `send_assign_notification`, `send_due_reminder`):**
```powershell
.venv\Scripts\python.exe -m celery -A app.worker.celery_app worker --loglevel=info --pool=solo
```
> `--pool=solo` cần thiết trên Windows (Celery không hỗ trợ tốt `prefork` trên Windows).

**3. Chạy Celery Beat (job định kỳ `remind_due_tasks`, 8h sáng mỗi ngày theo `CELERY_TIMEZONE`):**
```powershell
.venv\Scripts\python.exe -m celery -A app.worker.celery_app beat --loglevel=info
```

## Ngày 8: Docker compose, CLI seeder, debug

### Chạy toàn bộ stack bằng Docker

App + PostgreSQL + Redis + Celery worker + Celery beat + Mailpit + MinIO:
```powershell
copy .env.example .env   # neu chua co; compose doc SECRET_KEY... tu day
docker compose up -d --build
```
- API: http://127.0.0.1:8000/docs · Mailpit: http://127.0.0.1:8025 · MinIO console: http://127.0.0.1:9001 (`minioadmin`/`minioadmin`)
- Thứ tự khởi động: `migrate` (chạy `alembic upgrade head` 1 lần) và `minio-init` (tạo bucket) xong mới tới `app`/`worker`.
- File đính kèm lưu trên MinIO (`STORAGE_BACKEND=s3`). Postgres/Redis không mở port ra host (chỉ dùng trong network compose), dữ liệu nằm ở volume `postgres-data`, `minio-data`.
- Trùng port với container chạy tay ở các ngày trước (`taskhub-mailpit` dùng 8025) hoặc uvicorn local (8000): `docker stop taskhub-mailpit`, hoặc đổi port host qua biến `APP_PORT`, `MAILPIT_UI_PORT`, `MINIO_CONSOLE_PORT`, `DEBUGPY_PORT`.
- Dừng: `docker compose down` (thêm `-v` để xoá luôn dữ liệu).

> Image MinIO chính thức (`minio/minio`, `minio/mc`) đã bị gỡ khỏi Docker Hub/quay.io, compose dùng bản build cộng đồng `pgsty/minio` (cùng binary MinIO, có sẵn `mc`).

### CLI (Typer)

```powershell
# local
.venv\Scripts\python.exe -m app.cli --help
# trong docker
docker compose exec app python -m app.cli --help
```

| Lệnh | Mô tả |
|---|---|
| `seed --users 10 --projects 3 --tasks-per-project 10 [--password ...]` | Tạo dữ liệu mẫu: N member (`seed_member_001`...), mỗi project 1 PM riêng (`seed_pm_001`...) làm manager, task assign xoay vòng cho member, 5 tag mẫu. Password mặc định `Password123`. **Idempotent**: chạy lại chỉ tạo phần còn thiếu, tăng số lượng thì tạo thêm, giảm thì không xoá. Không gửi mail assign. |
| `create-admin --username admin --email admin@taskhub.dev` | Tạo tài khoản ADMIN (hỏi password ẩn nếu không truyền `--password`). Chạy lại với admin đã có thì không làm gì; username/email đang thuộc user thường thì báo lỗi, không tự nâng quyền. |
| `reset-db [--yes]` | **Xoá toàn bộ dữ liệu** (`DROP SCHEMA public`) rồi chạy lại migration từ đầu, xoá cache tag. Chỉ dùng khi dev. |

### Debug bằng debugpy (VSCode)

- Trong docker: `$env:DEBUGPY=1; docker compose up -d app` → VSCode chọn **Run and Debug → "TaskHub: attach (docker)"** (port 5678, chỉ bind `127.0.0.1`).
- Local: đặt `DEBUGPY=true` trong `.env`, chạy uvicorn như bình thường → **"TaskHub: attach (local)"**.
- Cần dừng ngay từ lúc startup thì đặt thêm `DEBUGPY_WAIT_FOR_CLIENT=true` (app chờ tới khi VSCode attach).
- Không bật `DEBUGPY` ở production (cổng debug cho phép chạy code tuỳ ý), và không dùng cùng `uvicorn --workers N` (các worker tranh nhau port).

### Logging & CORS

- Log format chung `thời gian LEVEL [logger] message`, mức log theo `LOG_LEVEL`; áp dụng cho API, Celery worker/beat và CLI.
- Mỗi request log 1 dòng `METHOD path -> status (x ms)` (4xx = WARNING, 5xx = ERROR; bỏ qua `/health`). Lỗi chưa được xử lý log kèm stacktrace và trả `500 {"error": {"message": "Internal server error"}}`.
- `CORS_ORIGINS`: JSON list origin của FE được gọi API từ trình duyệt, vd `["http://localhost:3000"]`.

## Chạy test (pytest)

Cài thêm dependency cho test (chỉ dùng khi dev, không cần trong image chạy app):
```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

**1. Tạo DB test riêng (chạy 1 lần, khớp `TEST_DATABASE_URL`):**
```powershell
docker exec -it taskhub-postgres psql -U taskhub -d taskhub -c "CREATE DATABASE taskhub_test OWNER taskhub"
```

**2. Chạy toàn bộ test suite** (không cần Redis/Celery đang chạy — `.delay()` được mock, Redis cache được thay bằng fake trong `tests/conftest.py`):
```powershell
.venv\Scripts\python.exe -m pytest
```
Test `test_mail_is_delivered_to_mailpit` gửi mail thật qua SMTP tới Mailpit rồi đọc lại qua API — tự skip nếu Mailpit không chạy.

## Test / Verify trên local

- http://127.0.0.1:8000/health → phải trả về `{"status":"ok"}`
- http://127.0.0.1:8000/docs → Swagger UI (danh sách endpoint sẽ đầy dần theo từng ngày, xem [docs/TASKS.md](docs/TASKS.md))

Kiểm tra bảng trong DB (tuỳ chọn):
```powershell
docker exec -it taskhub-postgres psql -U taskhub -d taskhub -c "\dt"
```

## Dừng môi trường

```powershell
docker stop taskhub-postgres
```
