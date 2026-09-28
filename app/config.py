from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_MAX_UPLOAD_SIZE


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
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


settings = Settings()
