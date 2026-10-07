"""Remote debug bang debugpy (Ngay 8): attach tu VSCode vao app dang chay
(local hoac trong container), cau hinh attach o `.vscode/launch.json`."""

import logging

import debugpy

from app.config import settings

logger = logging.getLogger(__name__)


def start_debugpy() -> None:
    """Mo cong debug khi DEBUGPY=1, mac dinh khong lam gi."""
    if not settings.debugpy:
        return
    debugpy.listen((settings.debugpy_host, settings.debugpy_port))
    logger.warning(
        "debugpy listening on %s:%d (DEBUGPY=1, never enable in production)",
        settings.debugpy_host,
        settings.debugpy_port,
    )
    if settings.debugpy_wait_for_client:
        logger.warning("Waiting for debugger to attach...")
        debugpy.wait_for_client()
