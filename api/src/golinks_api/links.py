import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from golinks_api.db import SessionDep
from golinks_api.errors import ApiError, error_responses, field_error
from golinks_api.models import Link
from golinks_api.schemas import ErrorDetail, LinkCreate, LinkList, LinkOut
from golinks_api.settings import SettingsDep

router = APIRouter(prefix="/api/links", tags=["links"])
logger = logging.getLogger("golinks.links")


@router.get("", response_model=LinkList, responses=error_responses())
def list_links(session: SessionDep) -> LinkList:
    links = session.scalars(select(Link).order_by(Link.slug))
    return LinkList(items=[LinkOut.model_validate(link) for link in links])


@router.post("", status_code=201, response_model=LinkOut, responses=error_responses(409, 422))
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


@router.get("/{slug}", response_model=LinkOut, responses=error_responses(404, 422))
def get_link(slug: str, session: SessionDep) -> LinkOut:
    link = session.scalar(select(Link).where(Link.slug == slug.strip().lower()))
    if link is None:
        raise ApiError(404, "link_not_found", f"go/{slug} doesn't exist.")
    return LinkOut.model_validate(link)
