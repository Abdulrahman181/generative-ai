"""Centralized application exceptions.

Services raise these; the exception handlers in ``handlers.py``
translate them into HTTP responses.  This keeps services free from
any FastAPI import.
"""


class AppException(Exception):
    """Base for all domain exceptions."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(detail, status_code=404)


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource already exists.") -> None:
        super().__init__(detail, status_code=409)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Invalid credentials.") -> None:
        super().__init__(detail, status_code=401)


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Access denied.") -> None:
        super().__init__(detail, status_code=403)


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation error.") -> None:
        super().__init__(detail, status_code=422)


class FileTooLargeError(AppException):
    def __init__(self, detail: str = "File is too large.") -> None:
        super().__init__(detail, status_code=413)
