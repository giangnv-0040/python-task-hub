# TaskHub API

Task Management API xây dựng bằng FastAPI, theo lộ trình tutorial-driven 8 ngày (xây dần 1 sample app từ skeleton đến production-ready).

- Đặc tả kỹ thuật (entities, roles, endpoint): [docs/SPEC.md](docs/SPEC.md)
- Kế hoạch 8 ngày: [docs/PLAN.md](docs/PLAN.md)
- Checklist tiến độ: [docs/TASKS.md](docs/TASKS.md)

## Tech stack

FastAPI · SQLAlchemy 2.x (async) · Alembic · Pydantic v2 · PostgreSQL 16 · Redis · Docker

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

**1. Bật Redis (broker/backend Celery + cache `GET /api/v1/tags`) và Mailpit (SMTP giả lập khi dev):**
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
