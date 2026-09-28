from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class StorageFileNotFoundError(Exception):
    """File khong ton tai tren storage (vd bi xoa tay ngoai he thong)."""


class StorageBackend(ABC):
    """Interface luu tru file dinh kem, doi duoc giua local disk va S3.

    Moi method deu lam viec theo stream chunk, khong giu ca file trong RAM.
    """

    @abstractmethod
    async def save(self, key: str, chunks: AsyncIterator[bytes]) -> None:
        """Ghi lan luot cac chunk vao `key`. Neu stream raise giua chung, phan da
        ghi phai duoc don dep truoc khi re-raise."""

    @abstractmethod
    async def open(self, key: str) -> AsyncIterator[bytes]:
        """Tra ve iterator doc file theo chunk. Raise `StorageFileNotFoundError`
        ngay khi goi (truoc khi bat dau stream) neu file khong ton tai."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Xoa file; khong loi neu file da khong con."""
