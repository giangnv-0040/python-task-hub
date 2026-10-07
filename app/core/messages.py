PROJECT_NOT_FOUND = "Project not found"
TAG_NOT_FOUND = "Tag not found"
USER_NOT_FOUND = "User not found"
TASK_NOT_FOUND = "Task not found"
USERNAME_ALREADY_EXISTS = "Username already exists"
EMAIL_ALREADY_EXISTS = "Email already exists"
INVALID_CREDENTIALS = "Incorrect username or password"
INVALID_TOKEN = "Could not validate credentials"
FIELD_NOT_NULLABLE = "Field cannot be null"
DUE_DATE_IN_PAST = "Due date cannot be in the past"
ACCOUNT_INACTIVE = "Account is inactive"
PERMISSION_DENIED = "You do not have permission to perform this action"
TASK_ALREADY_BOOKMARKED = "Task already bookmarked"
MANAGER_NOT_FOUND = "Manager not found, inactive or not a PM"
ASSIGNEE_NOT_FOUND = "Assignee not found or inactive"
COMMENT_NOT_FOUND = "Comment not found"
ATTACHMENT_NOT_FOUND = "Attachment not found"
ATTACHMENT_FILE_MISSING = "Attachment file is missing from storage"
FILENAME_REQUIRED = "Uploaded file must have a filename"
FILE_TOO_LARGE = "File exceeds the maximum upload size"
UNSUPPORTED_FILE_TYPE = "File type is not allowed"
INTERNAL_SERVER_ERROR = "Internal server error"

# Email thong bao (Ngay 7, app/worker/tasks.py) - dung str.format()
EMAIL_COMMENT_SUBJECT = "[TaskHub] New comment on task '{task_title}'"
EMAIL_COMMENT_BODY = "{author} commented on task '{task_title}':\n\n{content}"
EMAIL_ASSIGN_SUBJECT = "[TaskHub] You were assigned to task '{task_title}'"
EMAIL_ASSIGN_BODY = "{assigner} assigned task '{task_title}' to you."
EMAIL_DUE_REMINDER_SUBJECT = "[TaskHub] Task '{task_title}' is due soon"
EMAIL_DUE_REMINDER_BODY = "Task '{task_title}' is due on {due_date}."

# CLI (Ngay 8, app/cli.py)
CLI_SEED_DONE = (
    "Seed done: {users} users, {projects} projects, {tasks} tasks, {tags} tags created"
)
CLI_ADMIN_CREATED = "Admin '{username}' created"
CLI_ADMIN_ALREADY_EXISTS = "Admin '{username}' already exists, nothing to do"
CLI_USERNAME_TAKEN_BY_NON_ADMIN = "Username '{username}' already exists and is not an admin"
CLI_SEED_USER_CONFLICT = (
    "User '{username}' already exists but is not an active {role}, rename or remove it"
)
CLI_RESET_DB_CONFIRM = "Drop ALL data in {database} and re-run migrations?"
CLI_RESET_DB_DONE = "Database reset to latest migration"
