import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    can_manage_project,
    get_current_active_user,
    get_current_user,
    verify_admin_role,
    verify_attachment_owner_or_manager,
    verify_comment_owner_or_manager,
    verify_project_manager,
    verify_task_manager,
)
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token
from app.crud import attachment as crud_attachment
from app.crud import comment as crud_comment
from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate
from tests.conftest import make_project, make_task, make_user

# ---- get_current_user / get_current_active_user ----------------------------


async def test_get_current_user_without_token_is_unauthorized(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(UnauthorizedException):
        await get_current_user(token=None, db=db_session)


async def test_get_current_user_with_garbage_token_is_unauthorized(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(UnauthorizedException):
        await get_current_user(token="garbage", db=db_session)


async def test_get_current_user_for_deleted_user_is_unauthorized(
    db_session: AsyncSession,
) -> None:
    # Token chu ky hop le nhung user khong (con) ton tai
    with pytest.raises(UnauthorizedException):
        await get_current_user(token=create_access_token("ghost"), db=db_session)


async def test_get_current_user_ok(db_session: AsyncSession, member_user: User) -> None:
    token = create_access_token(member_user.username)
    assert (await get_current_user(token=token, db=db_session)).id == member_user.id


async def test_get_current_active_user_rejects_inactive(db_session: AsyncSession) -> None:
    locked = await make_user(db_session, "locked", is_active=False)
    with pytest.raises(ForbiddenException):
        await get_current_active_user(current_user=locked)


# ---- verify_admin_role / can_manage_project / verify_project_manager -------


async def test_verify_admin_role(
    admin_user: User, pm_user: User, member_user: User
) -> None:
    assert await verify_admin_role(current_user=admin_user) is admin_user
    for user in (pm_user, member_user):
        with pytest.raises(ForbiddenException):
            await verify_admin_role(current_user=user)


async def test_can_manage_project_rules(
    db_session: AsyncSession, admin_user: User, pm_user: User, member_user: User
) -> None:
    other_pm = await make_user(db_session, "pm2", role=UserRole.PM)
    own = await make_project(db_session, manager=pm_user)
    others = await make_project(db_session, manager=other_pm)

    assert can_manage_project(admin_user, others) is True
    assert can_manage_project(admin_user, None) is True
    assert can_manage_project(pm_user, own) is True
    assert can_manage_project(pm_user, others) is False
    assert can_manage_project(pm_user, None) is False
    # MEMBER khong quan ly project nao, ke ca khi bi gan nham lam manager
    member_managed = Project(name="x", manager_id=member_user.id)
    assert can_manage_project(member_user, member_managed) is False


async def test_verify_project_manager(
    db_session: AsyncSession, pm_user: User, member_user: User
) -> None:
    own = await make_project(db_session, manager=pm_user)
    assert await verify_project_manager(current_user=pm_user, project=own) is own
    with pytest.raises(ForbiddenException):
        await verify_project_manager(current_user=member_user, project=own)


async def test_verify_task_manager(
    db_session: AsyncSession, admin_user: User, pm_user: User, member_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session, manager=pm_user), admin_user)
    assert await verify_task_manager(current_user=pm_user, task=task, db=db_session) is task
    with pytest.raises(ForbiddenException):
        await verify_task_manager(current_user=member_user, task=task, db=db_session)


# ---- quyen cap object: comment / attachment --------------------------------


async def _comment_by(db_session: AsyncSession, task: Task, author: User) -> Comment:
    return await crud_comment.create_comment(
        db_session, task.id, CommentCreate(content="hi"), author_id=author.id
    )


async def test_verify_comment_owner_or_manager(
    db_session: AsyncSession, admin_user: User, pm_user: User, member_user: User
) -> None:
    other_member = await make_user(db_session, "member2")
    task = await make_task(db_session, await make_project(db_session, manager=pm_user), admin_user)
    comment = await _comment_by(db_session, task, member_user)

    for allowed in (member_user, pm_user, admin_user):
        result = await verify_comment_owner_or_manager(
            comment_id=comment.id, current_user=allowed, task=task, db=db_session
        )
        assert result.id == comment.id
    with pytest.raises(ForbiddenException):
        await verify_comment_owner_or_manager(
            comment_id=comment.id, current_user=other_member, task=task, db=db_session
        )


async def test_verify_comment_owner_or_manager_comment_of_other_task_not_found(
    db_session: AsyncSession, admin_user: User
) -> None:
    project = await make_project(db_session)
    task = await make_task(db_session, project, admin_user)
    other_task = await make_task(db_session, project, admin_user)
    comment = await _comment_by(db_session, task, admin_user)
    with pytest.raises(NotFoundException):
        await verify_comment_owner_or_manager(
            comment_id=comment.id, current_user=admin_user, task=other_task, db=db_session
        )


async def _attachment_by(db_session: AsyncSession, task: Task, uploader: User) -> Attachment:
    return await crud_attachment.create_attachment(
        db_session,
        task_id=task.id,
        uploaded_by=uploader.id,
        filename="a.txt",
        storage_key=f"key-{task.id}-{uploader.id}",
        content_type="text/plain",
        size=1,
    )


async def test_verify_attachment_owner_or_manager(
    db_session: AsyncSession, admin_user: User, pm_user: User, member_user: User
) -> None:
    other_member = await make_user(db_session, "member2")
    task = await make_task(db_session, await make_project(db_session, manager=pm_user), admin_user)
    attachment = await _attachment_by(db_session, task, member_user)

    for allowed in (member_user, pm_user, admin_user):
        result = await verify_attachment_owner_or_manager(
            current_user=allowed, attachment=attachment, db=db_session
        )
        assert result is attachment
    with pytest.raises(ForbiddenException):
        await verify_attachment_owner_or_manager(
            current_user=other_member, attachment=attachment, db=db_session
        )
