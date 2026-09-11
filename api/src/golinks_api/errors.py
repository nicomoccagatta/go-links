from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from golinks_api.observability import request_id_var
from golinks_api.schemas import ErrorBody, ErrorDetail, ErrorResponse

VALIDATION_MESSAGE = "Some fields are invalid."
HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def field_error(field: str, message: str) -> ApiError:
    """A 422 for rules the schema can't check on its own (e.g. ones that depend on settings)."""
    return ApiError(
        422, "validation_error", VALIDATION_MESSAGE, [ErrorDetail(field=field, message=message)]
    )


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    error = ErrorBody(code=code, message=message, request_id=request_id_var.get(), details=details)
    body = ErrorResponse(error=error).model_dump(exclude_none=True)
    return JSONResponse(body, status_code=status_code, headers=headers)


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` for a route, so generated clients see the error envelope (500 always)."""
    return {status_code: {"model": ErrorResponse} for status_code in (*status_codes, 500)}


def _field_name(loc: Sequence[str | int]) -> str:
    # ("body", "slug") -> "slug"; a body that isn't a JSON object -> "body".
    return ".".join(str(part) for part in loc[1:]) or str(loc[0])


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(field=_field_name(error["loc"]), message=error["msg"])
            for error in exc.errors()
        ]
        return error_response(422, "validation_error", VALIDATION_MESSAGE, details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, exc.detail, headers=exc.headers)
