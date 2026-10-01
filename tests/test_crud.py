from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Pagination
from app.crud import attachment as crud_attachment
from app.crud import bookmark as crud_bookmark
from app.crud import comment as crud_comment
from app.crud import project as crud_project
from app.crud import tag as crud_tag
from app.crud import task as crud_task
from app.crud import user as crud_user
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.tag import TagCreate, TagUpdate
from app.schemas.task import TaskCreate
from app.schemas.user import UserCreate, UserUpdate
from tests.conftest import DEFAULT_TEST_PASSWORD, make_project, make_task

# ---- crud/tag.py ----------------------------------------------------------


async def test_create_and_get_tag(db_session: AsyncSession) -> None:
    tag = await crud_tag.create_tag(db_session, TagCreate(name="backend", color="blue"))
    fetched = await crud_tag.get_tag(db_session, tag.id)
    assert fetched is not None
    assert fetched.name == "backend"


async def test_get_tags_returns_all(db_session: AsyncSession) -> None:
    await crud_tag.create_tag(db_session, TagCreate(name="t1", color="red"))
    await crud_tag.create_tag(db_session, TagCreate(name="t2", color="green"))
    assert {t.name for t in await crud_tag.get_tags(db_session)} == {"t1", "t2"}


async def test_update_tag_only_changes_sent_fields(db_session: AsyncSession) -> None:
    tag = await crud_tag.create_tag(db_session, TagCreate(name="t1", color="red"))
    updated = await crud_tag.update_tag(db_session, tag, TagUpdate(color="green"))
    assert (updated.name, updated.color) == ("t1", "green")


async def test_delete_tag(db_session: AsyncSession) -> None:
    tag = await crud_tag.create_tag(db_session, TagCreate(name="t1", color="red"))
    await crud_tag.delete_tag(db_session, tag)
    assert await crud_tag.get_tag(db_session, tag.id) is None


# ---- crud/project.py -------------------------------------------------------


async def test_create_and_update_project(db_session: AsyncSession) -> None:
    project = await crud_project.create_project(
        db_session, ProjectCreate(name="TaskHub", description="desc")
    )
    updated = await crud_project.update_project(
        db_session, project, ProjectUpdate(name="Renamed")
    )
    assert (updated.name, updated.description) == ("Renamed", "desc")


async def test_get_project_not_found_returns_none(db_session: AsyncSession) -> None:
    assert await crud_project.get_project(db_session, 999999) is None


async def test_delete_project_cascades_tasks(
    db_session: AsyncSession, admin_user: User
) -> None:
    project = await make_project(db_session)
    task = await make_task(db_session, project, admin_user)
    await crud_project.delete_project(db_session, project)
    assert await crud_task.get_task(db_session, task.id) is None


# ---- crud/user.py ----------------------------------------------------------


async def test_create_user_and_lookup(db_session: AsyncSession) -> None:
    data = UserCreate(
        username="alice",
        email="alice@example.com",
        full_name="Alice",
        password=DEFAULT_TEST_PASSWORD,
    )
    user = await crud_user.create_user(db_session, data, hashed_password="hashed")

    by_username = await crud_user.get_user_by_username(db_session, "alice")
    by_email = await crud_user.get_user_by_email(db_session, "alice@example.com")
    assert by_username is not None and by_username.id == user.id
    assert by_email is not None and by_email.id == user.id
    assert await crud_user.get_user_by_username(db_session, "nobody") is None


async def test_update_user(db_session: AsyncSession, member_user: User) -> None:
    updated = await crud_user.update_user(db_session, member_user, UserUpdate(full_name="New"))
    assert updated.full_name == "New"
    assert updated.email == member_user.email


# ---- crud/task.py ----------------------------------------------------------


async def test_create_task_uses_defaults(db_session: AsyncSession, admin_user: User) -> None:
    project = await make_project(db_session)
    task = await crud_task.create_task(
        db_session, project.id, TaskCreate(title="T"), created_by=admin_user.id
    )
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.MEDIUM
    assert task.created_by == admin_user.id
    assert task.tags == []


async def test_get_tasks_filters_and_paginates(
    db_session: AsyncSession, admin_user: User
) -> None:
    project = await make_project(db_session)
    for i in range(3):
        await make_task(
            db_session, project, admin_user, title=f"H{i}", priority=TaskPriority.HIGH
        )
    await make_task(db_session, project, admin_user, title="L", priority=TaskPriority.LOW)
    await make_task(
        db_session,
        project,
        admin_user,
        title="D",
        priority=TaskPriority.HIGH,
        status=TaskStatus.DONE,
    )

    high = await crud_task.get_tasks(
        db_session, Pagination(skip=0, limit=10), priority=TaskPriority.HIGH
    )
    assert [t.title for t in high] == ["H0", "H1", "H2", "D"]

    high_todo_second = await crud_task.get_tasks(
        db_session,
        Pagination(skip=1, limit=1),
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
    )
    assert [t.title for t in high_todo_second] == ["H1"]


async def test_get_tasks_by_project_only_returns_that_project(
    db_session: AsyncSession, admin_user: User
) -> None:
    p1 = await make_project(db_session, "P1")
    p2 = await make_project(db_session, "P2")
    await make_task(db_session, p1, admin_user, title="in-p1")
    await make_task(db_session, p2, admin_user, title="in-p2")
    tasks = await crud_task.get_tasks_by_project(
        db_session, p1.id, Pagination(skip=0, limit=10)
    )
    assert [t.title for t in tasks] == ["in-p1"]


async def test_assign_task(
    db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session), admin_user)
    updated = await crud_task.assign_task(db_session, task, member_user.id)
    assert updated.assignee_id == member_user.id


# ---- crud/comment.py -------------------------------------------------------


async def test_get_task_comment_is_scoped_by_task(
    db_session: AsyncSession, admin_user: User
) -> None:
    project = await make_project(db_session)
    task = await make_task(db_session, project, admin_user)
    other_task = await make_task(db_session, project, admin_user)
    comment = await crud_comment.create_comment(
        db_session, task.id, CommentCreate(content="hi"), author_id=admin_user.id
    )
    assert await crud_comment.get_task_comment(db_session, task.id, comment.id) is not None
    # comment_id dung nhung thuoc task khac -> coi nhu khong ton tai
    assert await crud_comment.get_task_comment(db_session, other_task.id, comment.id) is None

    await crud_comment.delete_comment(db_session, comment)
    assert await crud_comment.get_task_comment(db_session, task.id, comment.id) is None


# ---- crud/bookmark.py ------------------------------------------------------


async def test_create_bookmark_twice_returns_false(
    db_session: AsyncSession, admin_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session), admin_user)
    assert await crud_bookmark.create_bookmark(db_session, admin_user.id, task.id) is True
    assert await crud_bookmark.create_bookmark(db_session, admin_user.id, task.id) is False


# ---- crud/attachment.py ----------------------------------------------------


async def test_get_attachments_by_task_returns_page_and_total(
    db_session: AsyncSession, admin_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session), admin_user)
    for i in range(3):
        await crud_attachment.create_attachment(
            db_session,
            task_id=task.id,
            uploaded_by=admin_user.id,
            filename=f"f{i}.txt",
            storage_key=f"key{i}",
            content_type="text/plain",
            size=1,
        )
    items, total = await crud_attachment.get_attachments_by_task(
        db_session, task.id, Pagination(skip=1, limit=1)
    )
    assert total == 3
    assert [a.filename for a in items] == ["f1.txt"]
