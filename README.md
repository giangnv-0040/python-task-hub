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
