FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Cai dependency truoc khi copy code -> sua code khong phai cai lai tu dau (cache layer)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Khong chay bang root; thu muc storage cho STORAGE_BACKEND=local
RUN useradd --create-home --uid 1000 taskhub \
    && mkdir -p /app/storage \
    && chown taskhub:taskhub /app/storage
USER taskhub

EXPOSE 8000

# Access log cua uvicorn da tat trong app/core/logging.py (middleware log thay)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
