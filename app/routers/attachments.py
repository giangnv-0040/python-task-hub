from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.constants import (
    ATTACHMENT_NOT_FOUND_RESPONSE,
    TASK_NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.core.deps import (
    AttachmentDetailDep,
    CurrentUser,
    DbSession,
    TaskDetailDep,
    get_current_active_user,
    verify_attachment_owner_or_manager,
)
from app.core.pagination import PaginationDep
from app.crud import attachment as crud_attachment
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentRead
from app.schemas.base import Page
from app.services import attachment as attachment_service
from app.storage import StorageDep

# Route upload/list nested URL duoi /tasks nhung thao tac tren Attachment (R18)
task_attachments_router = APIRouter(
    prefix="/tasks/{task_id}/attachments", tags=["attachments"]
)

router = APIRouter(prefix="/attachments", tags=["attachments"])


@task_attachments_router.post(
    "",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file đính kèm cho task",
    description=(
        "File được đọc theo chunk và ghi thẳng vào storage (local/S3), không load "
        "cả file vào RAM. Giới hạn kích thước theo `MAX_UPLOAD_SIZE`, chỉ nhận "
        "content type trong whitelist."
    ),
    responses={
        **UNAUTHORIZED_RESPONSE,
        **TASK_NOT_FOUND_RESPONSE,
        400: {"description": "File không có tên"},
        413: {"description": "File vượt quá kích thước cho phép"},
        415: {"description": "Loại file không được hỗ trợ"},
    },
)
async def upload_attachment(
    file: UploadFile,
    current_user: CurrentUser,
    task: TaskDetailDep,
    db: DbSession,
    storage: StorageDep,
) -> AttachmentRead:
    attachment = await attachment_service.upload_attachment(
        db, storage, task_id=task.id, uploaded_by=current_user.id, file=file
    )
    return AttachmentRead.model_validate(attachment)


@task_attachments_router.get(
    "",
    response_model=Page[AttachmentRead],
    summary="Danh sách file đính kèm của task (phân trang)",
    responses={**UNAUTHORIZED_RESPONSE, **TASK_NOT_FOUND_RESPONSE},
    dependencies=[Depends(get_current_active_user)],
)
async def list_task_attachments(
    pagination: PaginationDep,
    task: TaskDetailDep,
    db: DbSession,
) -> Page[AttachmentRead]:
    attachments, total = await crud_attachment.get_attachments_by_task(
        db, task.id, pagination
    )
    return Page(items=[AttachmentRead.model_validate(a) for a in attachments], total=total)


@router.get(
    "/{attachment_id}/download",
    response_class=StreamingResponse,
    summary="Tải file đính kèm (stream)",
    responses={
        200: {"content": {"application/octet-stream": {}}},
        **UNAUTHORIZED_RESPONSE,
        404: {"description": "Attachment không tồn tại hoặc file đã mất trên storage"},
    },
    dependencies=[Depends(get_current_active_user)],
)
async def download_attachment(
    attachment: AttachmentDetailDep,
    storage: StorageDep,
) -> StreamingResponse:
    chunks = await attachment_service.open_attachment(storage, attachment)
    return StreamingResponse(
        chunks,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": attachment_service.content_disposition(
                attachment.filename
            ),
            "Content-Length": str(attachment.size),
        },
    )


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá file đính kèm (người upload, PM của project hoặc Admin)",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **ATTACHMENT_NOT_FOUND_RESPONSE,
        403: {"description": "Không phải người upload, PM của project hoặc Admin"},
    },
)
async def delete_attachment(
    attachment: Annotated[Attachment, Depends(verify_attachment_owner_or_manager)],
    db: DbSession,
    storage: StorageDep,
) -> None:
    await attachment_service.delete_attachment(db, storage, attachment)
