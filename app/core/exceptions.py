class AppException(Exception):
    """Base exception cho các lỗi nghiệp vụ, trả về response format chung."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=404, message=message)
