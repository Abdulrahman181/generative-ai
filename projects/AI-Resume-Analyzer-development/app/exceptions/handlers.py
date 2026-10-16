"""FastAPI exception handlers — translate domain exceptions to HTTP responses."""

from fastapi import Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppException


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(loc) for loc in first["loc"] if loc != "body")
    msg = first["msg"]
    detail = f"{field}: {msg}" if field else msg
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )


async def http_exception_handler_wrapper(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return await http_exception_handler(request, exc)
