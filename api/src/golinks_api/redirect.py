import logging
from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy import update

from golinks_api.db import SessionDep
from golinks_api.errors import error_responses
from golinks_api.models import Link
from golinks_api.observability import REDIRECTS
from golinks_api.settings import SettingsDep

router = APIRouter(tags=["redirect"])
logger = logging.getLogger("golinks.redirect")


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
