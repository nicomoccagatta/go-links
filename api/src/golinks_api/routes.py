import logging
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from golinks_api.db import Link, SessionDep
from golinks_api.errors import ApiError, error_responses, field_error
from golinks_api.observability import REDIRECTS
from golinks_api.schemas import ErrorDetail, Health, LinkCreate, LinkList, LinkOut
from golinks_api.settings import SettingsDep

router = APIRouter()
logger = logging.getLogger("golinks")


@router.get("/api/links", response_model=LinkList, responses=error_responses())
def list_links(session: SessionDep) -> LinkList:
    links = session.scalars(select(Link).order_by(Link.slug))
    return LinkList(items=[LinkOut.model_validate(link) for link in links])


@router.post(
    "/api/links", status_code=201, response_model=LinkOut, responses=error_responses(409, 422)
)
def create_link(
    body: LinkCreate, response: Response, session: SessionDep, settings: SettingsDep
) -> LinkOut:
    points_back_at_go = (
        urlsplit(body.target_url).hostname == urlsplit(settings.go_base_url).hostname
    )
    if points_back_at_go:
        raise field_error(
            "target_url", "Can't point at go links itself: it would redirect in a loop."
        )

    link = Link(slug=body.slug, target_url=body.target_url, description=body.description)
    session.add(link)
    # Let the unique constraint decide: check-then-insert races between concurrent creates.
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(
            409,
            "slug_taken",
            f"go/{body.slug} already exists.",
            [ErrorDetail(field="slug", message=f"go/{body.slug} is already taken.")],
        ) from None

    logger.info("link_created", extra={"slug": link.slug})
    response.headers["Location"] = f"/api/links/{link.slug}"
    return LinkOut.model_validate(link)


@router.get("/api/links/{slug}", response_model=LinkOut, responses=error_responses(404, 422))
def get_link(slug: str, session: SessionDep) -> LinkOut:
    link = session.scalar(select(Link).where(Link.slug == slug.strip().lower()))
    if link is None:
        raise ApiError(404, "link_not_found", f"go/{slug} doesn't exist.")
    return LinkOut.model_validate(link)


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


# Last: /{slug} matches every single-segment path, so it must come after the routes above.
# 302, not 301: browsers cache a 301 forever, so changing a link's target would silently not apply.
@router.get(
    "/{slug}",
    response_class=RedirectResponse,
    status_code=302,
    responses={
        302: {"description": "To the link's target, or to the create page if it doesn't exist."},
        **error_responses(422),
    },
)
def follow_link(slug: str, session: SessionDep, settings: SettingsDep) -> RedirectResponse:
    slug = slug.strip().lower()
    # One atomic UPDATE ... RETURNING: counts the visit and fetches the target, no lost increments.
    target_url = session.scalar(
        update(Link)
        .where(Link.slug == slug)
        .values(visit_count=Link.visit_count + 1, last_visited_at=datetime.now(UTC))
        .returning(Link.target_url)
    )
    session.commit()

    hit = target_url is not None
    REDIRECTS.labels(result="hit" if hit else "miss").inc()
    logger.info("link_redirect", extra={"slug": slug, "hit": hit})

    if target_url is None:
        # A miss is an invitation to create the link.
        return RedirectResponse(
            f"{settings.frontend_url}/?{urlencode({'new': slug})}", status_code=302
        )
    return RedirectResponse(target_url, status_code=302)
