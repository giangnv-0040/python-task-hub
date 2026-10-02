from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception cho các lỗi nghiệp vụ, trả về response format chung."""

    def __init__(
        self, status_code: int, message: str, headers: dict[str, str] | None = None
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.headers = headers
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=404, message=message)


class ConflictException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=409, message=message)


class UnauthorizedException(AppException):
    def __init__(self, message: str) -> None:
        # RFC 6750: response 401 phai kem header WWW-Authenticate
        super().__init__(
            status_code=401, message=message, headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=403, message=message)


class BadRequestException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=400, message=message)


class PayloadTooLargeException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=413, message=message)


class UnsupportedMediaTypeException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=415, message=message)


def error_response(
    status_code: int, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    """Format loi chung cua toan API (R1): AppException handler va loi 500
    (RequestLoggingMiddleware) deu tra qua day."""
    return JSONResponse(
        status_code=status_code, content={"error": {"message": message}}, headers=headers
    )
