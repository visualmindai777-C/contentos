import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.error")


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Unauthorized(AppError):
    status_code = 401


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409


class TooManyRequests(AppError):
    status_code = 429


def _fail(message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"success": False, "error": message}, status_code=status_code)


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return _fail(exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        detail = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return _fail(detail, 422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        return _fail(str(exc.detail), exc.status_code)

    @app.exception_handler(IntegrityError)
    async def integrity_error(_: Request, exc: IntegrityError):
        return _fail("Registro duplicado o referencia inexistente", 409)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        logger.exception("unhandled error")
        return _fail("Error interno", 500)
