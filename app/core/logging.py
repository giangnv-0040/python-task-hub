"""Cau hinh logging tap trung (Ngay 8).

Goi `setup_logging()` 1 lan o entrypoint cua moi process (API, Celery worker/
beat, CLI). Code con lai chi `logger = logging.getLogger(__name__)` (R34).
"""

import logging.config

from app.config import settings
from app.core.constants import LOG_DATE_FORMAT, LOG_FORMAT


def setup_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            # Giu logger cua thu vien da tao truoc khi goi ham nay (uvicorn,
            # celery, sqlalchemy...), chi doi handler/format
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": LOG_FORMAT, "datefmt": LOG_DATE_FORMAT}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "null": {"class": "logging.NullHandler"},
            },
            "root": {"level": settings.log_level, "handlers": ["console"]},
            "loggers": {
                # uvicorn tu gan handler rieng -> bo di, dung chung format qua root
                "uvicorn": {"handlers": [], "propagate": True},
                # RequestLoggingMiddleware da log moi request (kem thoi gian xu
                # ly) -> tat access log cua uvicorn de khong log 2 lan
                "uvicorn.access": {"handlers": ["null"], "propagate": False},
            },
        }
    )
