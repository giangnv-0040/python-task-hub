# Do dai field Pydantic khop voi gioi han cot DB tuong ung (xem app/models/*.py)

MIN_LENGTH_DEFAULT = 1

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 255
FULL_NAME_MAX_LENGTH = 255
PASSWORD_MIN_LENGTH = 8
# bcrypt chi hash 72 byte dau, phan sau bi bo am tham -> chan som o schema
PASSWORD_MAX_LENGTH = 72

TOKEN_TYPE_BEARER = "bearer"

PROJECT_NAME_MAX_LENGTH = 255

TAG_NAME_MAX_LENGTH = 50
TAG_COLOR_MAX_LENGTH = 20

TASK_TITLE_MAX_LENGTH = 255

# Cot comments.content la Text (khong gioi han), van chan o schema de tranh spam
COMMENT_CONTENT_MAX_LENGTH = 5000

ATTACHMENT_FILENAME_MAX_LENGTH = 255
ATTACHMENT_STORAGE_KEY_MAX_LENGTH = 64
ATTACHMENT_CONTENT_TYPE_MAX_LENGTH = 100

# Pagination (dung chung cho moi endpoint list, xem app/core/pagination.py)
DEFAULT_SKIP = 0
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# Mo ta ma loi dung chung cho `responses=` cua route decorator
UNAUTHORIZED_RESPONSE = {401: {"description": "Chưa đăng nhập hoặc token không hợp lệ"}}
PERMISSION_RESPONSES = {
    **UNAUTHORIZED_RESPONSE,
    403: {"description": "Không có quyền (chỉ PM của project hoặc Admin)"},
}
ADMIN_ONLY_RESPONSES = {
    **UNAUTHORIZED_RESPONSE,
    403: {"description": "Không có quyền (chỉ Admin)"},
}
PROJECT_NOT_FOUND_RESPONSE = {404: {"description": "Project không tồn tại"}}
TASK_NOT_FOUND_RESPONSE = {404: {"description": "Task không tồn tại"}}
TAG_NOT_FOUND_RESPONSE = {404: {"description": "Tag không tồn tại"}}
MANAGER_NOT_FOUND_RESPONSE = {404: {"description": "Manager không phải PM đang hoạt động"}}
PROJECT_MANAGER_NOT_FOUND_RESPONSE = {
    404: {"description": "Project không tồn tại, hoặc manager không phải PM đang hoạt động"}
}
PROJECT_ASSIGNEE_NOT_FOUND_RESPONSE = {
    404: {"description": "Project không tồn tại, hoặc assignee không tồn tại/bị khoá"}
}
TASK_ASSIGNEE_NOT_FOUND_RESPONSE = {
    404: {"description": "Task không tồn tại, hoặc assignee không tồn tại/bị khoá"}
}
ATTACHMENT_NOT_FOUND_RESPONSE = {404: {"description": "Attachment không tồn tại"}}

# Upload file (Ngay 6)
DEFAULT_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB, override qua env MAX_UPLOAD_SIZE
FILE_CHUNK_SIZE = 64 * 1024  # 64 KB moi lan doc/ghi, khong doc ca file vao RAM
# S3 multipart upload: moi part (tru part cuoi) toi thieu 5 MB
S3_MIN_PART_SIZE = 5 * 1024 * 1024
# Dependency ngoai (S3/MinIO) phai co timeout, khong de request treo vo han (R41)
S3_CONNECT_TIMEOUT_SECONDS = 5
S3_READ_TIMEOUT_SECONDS = 10
ALLOWED_UPLOAD_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/csv",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)
