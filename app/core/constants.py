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
# Redis (Ngay 7): cache GET /tags + timeout ket noi (khong de request treo vo
# han neu Redis khong phan hoi, tuong tu S3_*_TIMEOUT_SECONDS o tren)
TAGS_CACHE_KEY = "taskhub:tags:list"
REDIS_CONNECT_TIMEOUT_SECONDS = 2
REDIS_SOCKET_TIMEOUT_SECONDS = 2

# Celery (Ngay 7)
# Retry policy dung chung cho moi task gui mail (R43)
CELERY_MAX_RETRIES = 3
CELERY_RETRY_BACKOFF_SECONDS = 10
CELERY_RETRY_BACKOFF_MAX_SECONDS = 300
# Publish len broker chay trong request (sau commit): broker chet thi bo cuoc
# nhanh, khong giu request lau (R41). Mac dinh kombu retry 3 lan + khong timeout.
CELERY_PUBLISH_MAX_RETRIES = 1
CELERY_BROKER_SOCKET_TIMEOUT_SECONDS = 2
# Celery Beat: gio chay remind_due_tasks moi sang (theo CELERY_TIMEZONE)
REMIND_DUE_TASKS_HOUR = 8
REMIND_DUE_TASKS_MINUTE = 0
# Task "sap den han": due_date tu hom nay den het N ngay toi (due_date la date,
# khong co gio -> "trong 24h toi" = han hom nay hoac ngay mai)
DUE_SOON_DAYS = 1
SMTP_TIMEOUT_SECONDS = 10

# CORS (Ngay 8): FE goi API bang header Authorization (Bearer), khong dung
# cookie -> khong can allow_credentials. Expose Content-Disposition de FE doc
# duoc ten file khi download attachment.
CORS_ALLOW_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOW_HEADERS = ("Authorization", "Content-Type")
CORS_EXPOSE_HEADERS = ("Content-Disposition",)

# Logging (Ngay 8, app/core/logging.py)
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# Docker healthcheck goi /health moi vai giay -> khong log tung request
REQUEST_LOG_SKIP_PATHS = frozenset({"/health"})

# CLI seeder (Ngay 8, app/cli.py): username/ten co dinh theo so thu tu -> chay
# lai seed tim thay ban ghi cu thay vi tao trung
SEED_DEFAULT_USERS = 10
SEED_DEFAULT_PROJECTS = 3
SEED_DEFAULT_TASKS_PER_PROJECT = 10
# Password chung cua moi user seed - chi la du lieu dev/demo, doi qua --password
SEED_DEFAULT_PASSWORD = "Password123"
SEED_MEMBER_USERNAME = "seed_member_{index:03d}"
SEED_PM_USERNAME = "seed_pm_{index:03d}"
SEED_EMAIL_DOMAIN = "taskhub.dev"
SEED_PROJECT_NAME = "Seed Project {index:03d}"
SEED_TASK_TITLE = "Seed task {index:03d}"
# due_date cua task seed rai deu tu hom nay toi N ngay sau
SEED_DUE_DATE_SPREAD_DAYS = 14
SEED_TAGS = (
    ("bug", "red"),
    ("feature", "green"),
    ("backend", "blue"),
    ("frontend", "purple"),
    ("urgent", "orange"),
)

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
