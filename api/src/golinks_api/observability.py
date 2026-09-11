import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

from prometheus_client import Counter, Histogram
from starlette.requests import Request
from starlette.routing import Route

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Routes are labeled by template (/{slug}), never by raw path: raw slugs are unbounded label
# values, and anyone requesting random URLs could grow the series count without limit.
HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests.", ["method", "route", "status"])
HTTP_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request latency.", ["method", "route"]
)
REDIRECTS = Counter("golinks_redirects_total", "go/<slug> visits by lookup result.", ["result"])

_LOG_RECORD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line; fields passed via `extra=` become top-level keys."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get() or None,
        }
        entry |= {key: value for key, value in vars(record).items() if key not in _LOG_RECORD_ATTRS}
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # Our middleware writes the access line (with request_id and route); uvicorn's duplicates it.
    logging.getLogger("uvicorn.access").disabled = True


def route_label(request: Request) -> str:
    route = request.scope.get("route")
    return route.path if isinstance(route, Route) else "unmatched"
