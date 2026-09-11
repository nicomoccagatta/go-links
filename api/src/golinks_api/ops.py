import logging

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from golinks_api.db import SessionDep
from golinks_api.errors import ApiError, error_responses
from golinks_api.schemas import Health

router = APIRouter(tags=["ops"])
logger = logging.getLogger("golinks.ops")


@router.get("/healthz", response_model=Health, responses=error_responses(503))
def healthz(session: SessionDep) -> Health:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("healthcheck_failed")
        raise ApiError(503, "unavailable", "Database is unreachable.") from None
    return Health(status="ok")


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
