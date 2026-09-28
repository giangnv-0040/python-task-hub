"""Nghiep vu attachment: phoi hop storage backend + DB trong 1 cho (R13).

Storage va DB khong chung 1 transaction, nen thu tu thao tac duoc chon de
neu loi giua chung thi chi con file mo coi (vo hai), khong bao gio con row
tro toi file khong ton tai.
"""

import logging
import re
from collections.abc import AsyncIterator
from urllib.parse import quote
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import (
    ALLOWED_UPLOAD_CONTENT_TYPES,
    ATTACHMENT_FILENAME_MAX_LENGTH,
    FILE_CHUNK_SIZE,
)
from app.core.exceptions import (
    BadRequestException,
    NotFoundException,
    PayloadTooLargeException,
    UnsupportedMediaTypeException,
)
from app.core.messages import (
    ATTACHMENT_FILE_MISSING,
    FILE_TOO_LARGE,
    FILENAME_REQUIRED,
    UNSUPPORTED_FILE_TYPE,
)
from app.crud import attachment as crud_attachment
from app.models.attachment import Attachment
from app.storage import StorageBackend, StorageFileNotFoundError

PATH_SEPARATORS = re.compile(r"[\\/]")
logger = logging.getLogger(__name__)


def _normalize_content_type(content_type: str | None) -> str:
    # "text/plain; charset=utf-8" -> "text/plain"
    return (content_type or "").split(";")[0].strip().lower()


def _clean_filename(raw: str | None) -> str:
    # Mot so client gui kem duong dan ("C:\\x\\a.pdf") -> chi giu ten file;
    # bo ky tu dieu khien de khong pha vo header Content-Disposition.
    name = PATH_SEPARATORS.split(raw or "")[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    if not name:
        raise BadRequestException(FILENAME_REQUIRED)
    if len(name) <= ATTACHMENT_FILENAME_MAX_LENGTH:
        return name
    # Qua dai: cat phan ten, giu nguyen duoi file
    stem, dot, ext = name.rpartition(".")
    if not dot or len(ext) + 1 >= ATTACHMENT_FILENAME_MAX_LENGTH:
        return name[:ATTACHMENT_FILENAME_MAX_LENGTH]
    return f"{stem[: ATTACHMENT_FILENAME_MAX_LENGTH - len(ext) - 1]}.{ext}"


async def upload_attachment(
    db: AsyncSession,
    storage: StorageBackend,
    task_id: int,
    uploaded_by: int,
    file: UploadFile,
) -> Attachment:
    content_type = _normalize_content_type(file.content_type)
    if content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise UnsupportedMediaTypeException(UNSUPPORTED_FILE_TYPE)
    filename = _clean_filename(file.filename)
    # UUID lam storage key: khong dung ten file nguoi dung (path traversal / ghi de)
    storage_key = uuid4().hex
    size = 0

    async def read_chunks() -> AsyncIterator[bytes]:
        nonlocal size
        while chunk := await file.read(FILE_CHUNK_SIZE):
            size += len(chunk)
            if size > settings.max_upload_size:
                # storage.save tu don phan da ghi khi stream raise
                raise PayloadTooLargeException(FILE_TOO_LARGE)
            yield chunk

    await storage.save(storage_key, read_chunks())
    try:
        return await crud_attachment.create_attachment(
            db,
            task_id=task_id,
            uploaded_by=uploaded_by,
            filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            size=size,
        )
    except BaseException:
        await storage.delete(storage_key)
        raise


async def open_attachment(
    storage: StorageBackend, attachment: Attachment
) -> AsyncIterator[bytes]:
    try:
        return await storage.open(attachment.storage_key)
    except StorageFileNotFoundError as exc:
        # Row DB con nhung file mat tren storage la bat thuong (vd bi xoa tay
        # ngoai he thong) - dang duoc xu ly dung (404 ro rang), nhung van dang
        # log lai de biet ma kiem tra storage (R34)
        logger.warning(
            "Attachment %s exists in DB but file %s is missing from storage",
            attachment.id,
            attachment.storage_key,
        )
        raise NotFoundException(ATTACHMENT_FILE_MISSING) from exc


def content_disposition(filename: str) -> str:
    # RFC 6266: `filename` ASCII lam fallback, `filename*` UTF-8 cho ten tieng Viet
    ascii_fallback = filename.encode("ascii", "replace").decode().replace('"', "'")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


async def delete_attachment(
    db: AsyncSession, storage: StorageBackend, attachment: Attachment
) -> None:
    # Xoa row truoc: neu xoa file loi thi chi con file mo coi, API khong con tro toi
    await crud_attachment.delete_attachment(db, attachment)
    try:
        await storage.delete(attachment.storage_key)
    except Exception:
        # Thao tac chinh (xoa row DB) da thanh cong; loi o day chi con file mo coi
        # tren storage -> khong duoc lam hong response da thanh cong (R32). Chua co
        # logging tap trung (Ngay 8, R34) nen tam dung logger cuc bo o day.
        logger.exception(
            "Failed to delete storage object %s after DB delete (attachment %s)",
            attachment.storage_key,
            attachment.id,
        )
