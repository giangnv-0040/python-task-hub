from unittest.mock import MagicMock

from httpx import AsyncClient

from app.models.user import User
from tests.conftest import DEFAULT_TEST_PASSWORD


async def _login(client: AsyncClient, username: str) -> dict[str, str]:
    resp = await client.post(
        "/api/users/login", data={"username": username, "password": DEFAULT_TEST_PASSWORD}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_register_login_project_task_comment_attachment_flow(
    client: AsyncClient,
    admin_user: User,
    pm_user: User,
    celery_delay: dict[str, MagicMock],
) -> None:
    # register + login
    register_resp = await client.post(
        "/api/users/register",
        json={
            "username": "newmember",
            "email": "newmember@example.com",
            "full_name": "New Member",
            "password": DEFAULT_TEST_PASSWORD,
        },
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["role"] == "MEMBER"
    member_id = register_resp.json()["id"]

    admin_headers = await _login(client, admin_user.username)
    pm_headers = await _login(client, pm_user.username)
    member_headers = await _login(client, "newmember")

    me = await client.get("/api/users/me", headers=member_headers)
    assert me.json()["username"] == "newmember"

    # Admin tao project, giao cho PM quan ly
    project_resp = await client.post(
        "/api/projects",
        json={"name": "TaskHub", "manager_id": pm_user.id},
        headers=admin_headers,
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    # PM tao task trong project minh quan ly, assign luon cho member
    task_resp = await client.post(
        f"/api/projects/{project_id}/tasks",
        json={"title": "Setup CI", "assignee_id": member_id},
        headers=pm_headers,
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert (task["assignee_id"], task["created_by"]) == (member_id, pm_user.id)
    # Tao task kem assignee -> co job bao assign (chay sau khi commit)
    celery_delay["send_assign_notification"].assert_called_once_with(task["id"], pm_user.id)

    # member comment -> job bao comment
    comment_resp = await client.post(
        f"/api/tasks/{task['id']}/comments",
        json={"content": "  Working on it  "},
        headers=member_headers,
    )
    assert comment_resp.status_code == 201
    comment = comment_resp.json()
    assert (comment["author_id"], comment["content"]) == (member_id, "Working on it")
    celery_delay["send_comment_notification"].assert_called_once_with(comment["id"])

    # upload -> list -> download -> delete file dinh kem
    upload_resp = await client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": ("báo cáo.txt", b"hello world", "text/plain")},
        headers=member_headers,
    )
    assert upload_resp.status_code == 201
    attachment = upload_resp.json()
    assert (attachment["size"], attachment["uploaded_by"]) == (11, member_id)
    assert "storage_key" not in attachment

    list_resp = await client.get(
        f"/api/tasks/{task['id']}/attachments", headers=member_headers
    )
    assert list_resp.json()["total"] == 1

    download_resp = await client.get(
        f"/api/attachments/{attachment['id']}/download", headers=member_headers
    )
    assert download_resp.status_code == 200
    assert download_resp.content == b"hello world"
    assert download_resp.headers["content-type"].startswith("text/plain")
    assert "filename*=UTF-8''b%C3%A1o%20c%C3%A1o.txt" in download_resp.headers[
        "content-disposition"
    ]

    delete_resp = await client.delete(
        f"/api/attachments/{attachment['id']}", headers=member_headers
    )
    assert delete_resp.status_code == 204
    gone = await client.get(
        f"/api/attachments/{attachment['id']}/download", headers=member_headers
    )
    assert gone.status_code == 404

    # PM xoa comment cua member trong project minh quan ly
    delete_comment = await client.delete(
        f"/api/tasks/{task['id']}/comments/{comment['id']}", headers=pm_headers
    )
    assert delete_comment.status_code == 204


async def test_assign_task_enqueues_notification(
    client: AsyncClient,
    admin_user: User,
    member_user: User,
    celery_delay: dict[str, MagicMock],
) -> None:
    headers = await _login(client, admin_user.username)
    project_id = (
        await client.post("/api/projects", json={"name": "P"}, headers=headers)
    ).json()["id"]
    task_id = (
        await client.post(
            f"/api/projects/{project_id}/tasks", json={"title": "T"}, headers=headers
        )
    ).json()["id"]
    # Tao task khong co assignee -> chua bao ai
    celery_delay["send_assign_notification"].assert_not_called()

    resp = await client.post(
        f"/api/tasks/{task_id}/assign",
        json={"assignee_id": member_user.id},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["assignee_id"] == member_user.id
    celery_delay["send_assign_notification"].assert_called_once_with(task_id, admin_user.id)
