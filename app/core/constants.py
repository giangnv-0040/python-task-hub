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
