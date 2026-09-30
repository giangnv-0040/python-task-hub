from sqlalchemy import Column, ForeignKey, Table

from app.database import Base

task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

bookmarks = Table(
    "bookmarks",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    # Bang trung gian khong co relationship tren Task nen ORM khong tu xoa row;
    # ondelete=CASCADE de xoa task (vd khi xoa project) khong vuong FK (R10)
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
)
