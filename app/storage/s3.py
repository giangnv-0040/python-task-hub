from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Any

import aioboto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.constants import (
    FILE_CHUNK_SIZE,
    S3_CONNECT_TIMEOUT_SECONDS,
    S3_MIN_PART_SIZE,
    S3_READ_TIMEOUT_SECONDS,
)
from app.storage.base import StorageBackend, StorageFileNotFoundError

S3_NOT_FOUND_ERROR_CODES = frozenset({"NoSuchKey", "404"})
# Dependency ngoai (S3/MinIO) phai co timeout, khong de request treo vo han (R41)
_BOTO_CONFIG = BotoConfig(
    connect_timeout=S3_CONNECT_TIMEOUT_SECONDS, read_timeout=S3_READ_TIMEOUT_SECONDS
)


class S3Storage(StorageBackend):
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None,
        region: str,
        access_key: str | None,
        secret_key: str | None,
    ) -> None:
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def _client(self) -> Any:
        return self._session.client(
            "s3", endpoint_url=self._endpoint_url, config=_BOTO_CONFIG
        )

    async def save(self, key: str, chunks: AsyncIterator[bytes]) -> None:
        # File nho hon 1 part upload 1 lan bang put_object; chi mo multipart
        # upload khi buffer vuot S3_MIN_PART_SIZE -> RAM toi da ~1 part.
        async with self._client() as s3:
            upload_id: str | None = None
            parts: list[dict[str, Any]] = []
            buffer = bytearray()
            try:
                async for chunk in chunks:
                    buffer.extend(chunk)
                    if len(buffer) < S3_MIN_PART_SIZE:
                        continue
                    if upload_id is None:
                        created = await s3.create_multipart_upload(
                            Bucket=self._bucket, Key=key
                        )
                        upload_id = created["UploadId"]
                    parts.append(await self._upload_part(s3, key, upload_id, parts, buffer))
                    buffer.clear()

                if upload_id is None:
                    await s3.put_object(Bucket=self._bucket, Key=key, Body=bytes(buffer))
                    return
                if buffer:
                    parts.append(await self._upload_part(s3, key, upload_id, parts, buffer))
                await s3.complete_multipart_upload(
                    Bucket=self._bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
            except BaseException:
                if upload_id is not None:
                    await s3.abort_multipart_upload(
                        Bucket=self._bucket, Key=key, UploadId=upload_id
                    )
                raise

    async def _upload_part(
        self,
        s3: Any,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
        data: bytearray,
    ) -> dict[str, Any]:
        part_number = len(parts) + 1
        result = await s3.upload_part(
            Bucket=self._bucket,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=bytes(data),
        )
        return {"PartNumber": part_number, "ETag": result["ETag"]}

    async def open(self, key: str) -> AsyncIterator[bytes]:
        # Client phai song den khi stream xong -> giu bang AsyncExitStack va
        # dong trong generator, thay vi `async with` bao quanh lenh return.
        stack = AsyncExitStack()
        try:
            s3 = await stack.enter_async_context(self._client())
            obj = await s3.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            await stack.aclose()
            if exc.response["Error"]["Code"] in S3_NOT_FOUND_ERROR_CODES:
                raise StorageFileNotFoundError(key) from exc
            raise
        except BaseException:
            await stack.aclose()
            raise
        return self._iter_body(stack, obj["Body"])

    async def _iter_body(self, stack: AsyncExitStack, body: Any) -> AsyncIterator[bytes]:
        async with stack:
            while chunk := await body.read(FILE_CHUNK_SIZE):
                yield chunk

    async def delete(self, key: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=key)
