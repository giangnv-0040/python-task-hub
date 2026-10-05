from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
import aiofiles.os
from aiofiles.threadpool.binary import AsyncBufferedReader

from app.core.constants import FILE_CHUNK_SIZE
from app.storage.base import StorageBackend, StorageFileNotFoundError


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir).resolve()

    def _path(self, key: str) -> Path:
        path = (self._base_dir / key).resolve()
        # key luon do server sinh (UUID), van chan path traversal phong ho
        if path.parent != self._base_dir:
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    async def save(self, key: str, chunks: AsyncIterator[bytes]) -> None:
        path = self._path(key)
        await aiofiles.os.makedirs(self._base_dir, exist_ok=True)
        try:
            async with aiofiles.open(path, "wb") as f:
                async for chunk in chunks:
                    await f.write(chunk)
        except BaseException:
            await self.delete(key)
            raise

    async def open(self, key: str) -> AsyncIterator[bytes]:
        try:
            f = await aiofiles.open(self._path(key), "rb")
        except FileNotFoundError as exc:
            raise StorageFileNotFoundError(key) from exc
        return self._iter_file(f)

    async def _iter_file(self, f: AsyncBufferedReader) -> AsyncIterator[bytes]:
        try:
            while chunk := await f.read(FILE_CHUNK_SIZE):
                yield chunk
        finally:
            await f.close()

    async def delete(self, key: str) -> None:
        try:
            await aiofiles.os.remove(self._path(key))
        except FileNotFoundError:
            pass
