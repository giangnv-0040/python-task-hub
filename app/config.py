from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_MAX_UPLOAD_SIZE


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Prefix + version cho toan bo API, doi version chi can sua 1 cho (vd /api/v2)
    api_prefix: str = "/api/v1"

    database_url: str
    # In moi cau SQL kem tham so ra stdout -> chi bat khi debug local (R38)
    db_echo: bool = False
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    storage_backend: Literal["local", "s3"] = "local"
    max_upload_size: int = DEFAULT_MAX_UPLOAD_SIZE
    local_storage_dir: str = "storage"
    s3_bucket: str = "taskhub-attachments"
    s3_endpoint_url: str | None = None  # vd http://localhost:9000 khi dung MinIO
    s3_region: str = "us-east-1"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    # DB rieng cho pytest (app/database.py chi doc database_url); mac dinh
    # None -> tests/conftest.py tu suy ra tu database_url (them hau to _test)
    test_database_url: str | None = None

    # Redis (Ngay 7): cache GET /tags o db 0, broker/backend Celery tach db
    # rieng de FLUSHDB cache khong xoa mat hang doi job
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    # Timezone cho lich Celery Beat (REMIND_DUE_TASKS_HOUR tinh theo gio nay)
    celery_timezone: str = "Asia/Ho_Chi_Minh"
    tag_cache_ttl_seconds: int = 300

    # SMTP (Mailpit khi dev): app/core/mail.py
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    mail_from: str = "taskhub@example.com"


settings = Settings()
