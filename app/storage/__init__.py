from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.storage.base import StorageBackend, StorageFileNotFoundError
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage

__all__ = ["StorageBackend", "StorageFileNotFoundError", "StorageDep", "get_storage"]


@lru_cache
def get_storage() -> StorageBackend:
    """Dependency tra ve storage backend theo env STORAGE_BACKEND (1 instance/process)."""
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
        )
    return LocalStorage(settings.local_storage_dir)


StorageDep = Annotated[StorageBackend, Depends(get_storage)]
