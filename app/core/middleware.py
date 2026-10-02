"""Middleware dung chung (Ngay 8): log request + bat loi 500, CORS."""

import logging
import time

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.constants import (
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_EXPOSE_HEADERS,
    REQUEST_LOG_SKIP_PATHS,
)
from app.core.exceptions import error_response
from app.core.messages import INTERNAL_SERVER_ERROR

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log moi request: method, path, status, thoi gian xu ly (ms).

    Loi chua duoc exception handler nao xu ly (AppException, 422... da duoc
    FastAPI tra response truoc khi toi day) se noi len toi `call_next`: log
    stacktrace 1 lan o day roi tra 500 dung format loi chung (R1), khong de
    lot ra ServerErrorMiddleware (tra text "Internal Server Error" va uvicorn
    log stacktrace them lan nua).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Bat rong co chu dich: day la lop cuoi cung truoc khi tra 500, va
            # luon log kem stacktrace (R27, R34)
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            response = error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_SERVER_ERROR
            )
        if request.url.path not in REQUEST_LOG_SKIP_PATHS:
            self._log(request, response.status_code, time.perf_counter() - started)
        return response

    @staticmethod
    def _log(request: Request, status_code: int, elapsed_seconds: float) -> None:
        if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            level = logging.ERROR
        elif status_code >= status.HTTP_400_BAD_REQUEST:
            level = logging.WARNING
        else:
            level = logging.INFO
        logger.log(
            level,
            "%s %s -> %d (%.1f ms)",
            request.method,
            request.url.path,
            status_code,
            elapsed_seconds * 1000,
        )


def setup_middlewares(app: FastAPI, cors_origins: list[str]) -> None:
    # Middleware them sau nam ngoai: CORS boc ngoai RequestLoggingMiddleware ->
    # response 500 do middleware log tra ve van co header CORS, FE doc duoc loi
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
        expose_headers=CORS_EXPOSE_HEADERS,
    )
