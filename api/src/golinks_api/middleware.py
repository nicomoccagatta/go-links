import logging
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response

from golinks_api.errors import error_response
from golinks_api.observability import HTTP_DURATION, HTTP_REQUESTS, request_id_var, route_label

REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{1,128}")

logger = logging.getLogger("golinks")
access_logger = logging.getLogger("golinks.access")


async def observe_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Request ID, access log, metrics, and the 500 envelope for anything unhandled."""
    incoming_id = request.headers.get("x-request-id", "")
    request_id = incoming_id if REQUEST_ID_PATTERN.fullmatch(incoming_id) else str(uuid4())
    request_id_var.set(request_id)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled_exception")
        response = error_response(500, "internal_error", "Something went wrong on our side.")
    duration = time.perf_counter() - started

    route = route_label(request)
    HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    HTTP_DURATION.labels(request.method, route).observe(duration)
    access_logger.info(
        "request",
        extra={
            "method": request.method,
            "route": route,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response
