import logging
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import debug
from app.core.logging import setup_logging
from app.core.messages import INTERNAL_SERVER_ERROR
from app.core.middleware import setup_middlewares
from app.database import get_db
from app.main import app

MIDDLEWARE_LOGGER = "app.core.middleware"
FRONTEND_ORIGIN = "http://frontend.test"


async def _broken_db() -> AsyncGenerator[AsyncSession, None]:
    raise RuntimeError("database exploded")
    yield  # pragma: no cover - bien ham thanh generator dependency


# ---- Request logging -------------------------------------------------------


async def test_request_is_logged_with_status_and_duration(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=MIDDLEWARE_LOGGER):
        resp = await client.get("/api/tags")

    assert resp.status_code == 401
    [record] = [r for r in caplog.records if r.name == MIDDLEWARE_LOGGER]
    assert record.levelno == logging.WARNING
    assert record.getMessage().startswith("GET /api/tags -> 401 (")
    assert record.getMessage().endswith(" ms)")


async def test_health_check_is_not_logged(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=MIDDLEWARE_LOGGER):
        assert (await client.get("/health")).status_code == 200
    assert not [r for r in caplog.records if r.name == MIDDLEWARE_LOGGER]


async def test_unhandled_error_returns_500_in_common_format_and_logs_stacktrace(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[get_db] = _broken_db

    with caplog.at_level(logging.INFO, logger=MIDDLEWARE_LOGGER):
        resp = await client.get("/api/users/alice/profile")

    assert resp.status_code == 500
    assert resp.json() == {"error": {"message": INTERNAL_SERVER_ERROR}}
    # Khong lo chi tiet loi noi bo ra client
    assert "exploded" not in resp.text
    error_log, request_log = [r for r in caplog.records if r.name == MIDDLEWARE_LOGGER]
    assert error_log.exc_info is not None
    assert isinstance(error_log.exc_info[1], RuntimeError)
    assert request_log.levelno == logging.ERROR
    assert "-> 500" in request_log.getMessage()


# ---- CORS ------------------------------------------------------------------


@pytest.fixture
def cors_client() -> AsyncClient:
    """App rieng voi origin co dinh: app.main doc CORS_ORIGINS tu env luc import."""
    test_app = FastAPI()
    setup_middlewares(test_app, cors_origins=[FRONTEND_ORIGIN])

    @test_app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


async def test_cors_preflight_allows_configured_origin(cors_client: AsyncClient) -> None:
    resp = await cors_client.options(
        "/ok",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert "PATCH" in resp.headers["access-control-allow-methods"]


async def test_cors_rejects_unknown_origin(cors_client: AsyncClient) -> None:
    resp = await cors_client.get("/ok", headers={"Origin": "http://evil.test"})
    assert "access-control-allow-origin" not in resp.headers


async def test_cors_exposes_content_disposition_for_downloads(
    cors_client: AsyncClient,
) -> None:
    resp = await cors_client.get("/ok", headers={"Origin": FRONTEND_ORIGIN})
    assert resp.headers["access-control-expose-headers"] == "Content-Disposition"


async def test_cors_headers_present_on_500(cors_client: AsyncClient) -> None:
    # CORS boc ngoai middleware log -> FE van doc duoc body loi 500
    resp = await cors_client.get("/boom", headers={"Origin": FRONTEND_ORIGIN})
    assert resp.status_code == 500
    assert resp.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


# ---- Logging config & debugpy ----------------------------------------------


def test_setup_logging_uses_log_level_and_silences_uvicorn_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = logging.getLogger()
    original_level, original_handlers = root.level, root.handlers[:]
    monkeypatch.setattr(settings, "log_level", "DEBUG")
    try:
        setup_logging()
        assert root.level == logging.DEBUG
        access = logging.getLogger("uvicorn.access")
        assert access.propagate is False
        assert all(isinstance(h, logging.NullHandler) for h in access.handlers)
    finally:
        root.setLevel(original_level)
        root.handlers[:] = original_handlers


def test_debugpy_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    listen = MagicMock()
    monkeypatch.setattr(debug.debugpy, "listen", listen)
    monkeypatch.setattr(settings, "debugpy", False)

    debug.start_debugpy()

    listen.assert_not_called()


@pytest.mark.parametrize("wait_for_client", [False, True])
def test_debugpy_listens_on_configured_address(
    monkeypatch: pytest.MonkeyPatch, wait_for_client: bool
) -> None:
    listen, wait = MagicMock(), MagicMock()
    monkeypatch.setattr(debug.debugpy, "listen", listen)
    monkeypatch.setattr(debug.debugpy, "wait_for_client", wait)
    monkeypatch.setattr(settings, "debugpy", True)
    monkeypatch.setattr(settings, "debugpy_host", "0.0.0.0")
    monkeypatch.setattr(settings, "debugpy_port", 5679)
    monkeypatch.setattr(settings, "debugpy_wait_for_client", wait_for_client)

    debug.start_debugpy()

    listen.assert_called_once_with(("0.0.0.0", 5679))
    assert wait.called is wait_for_client
