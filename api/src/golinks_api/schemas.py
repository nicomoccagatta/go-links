import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
# Top-level paths the service itself serves; a link there would shadow them.
RESERVED_SLUGS = frozenset({"api", "healthz", "metrics", "docs", "redoc", "static"})
# Anything else (javascript:, data:, file:) would turn go/ into an XSS or phishing vector.
ALLOWED_SCHEMES = frozenset({"http", "https"})


class LinkCreate(BaseModel):
    slug: str
    target_url: str = Field(max_length=2048)
    description: str | None = Field(default=None, max_length=280)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        slug = value.strip().lower()
        # fullmatch: `$` alone would also accept a trailing newline.
        if not SLUG_PATTERN.fullmatch(slug):
            raise PydanticCustomError(
                "invalid_slug",
                "Use 1-64 lowercase letters, digits or hyphens, "
                "not starting or ending with a hyphen.",
            )
        if slug in RESERVED_SLUGS:
            raise PydanticCustomError("reserved_slug", "go/{slug} is reserved.", {"slug": slug})
        return slug

    @field_validator("target_url")
    @classmethod
    def check_target_url(cls, value: str) -> str:
        try:
            parts = urlsplit(value)
        except ValueError:
            parts = None
        is_web_url = parts is not None and parts.scheme in ALLOWED_SCHEMES
        has_host = parts is not None and bool(parts.hostname)
        has_whitespace = any(char.isspace() for char in value)
        if not is_web_url or not has_host or has_whitespace:
            raise PydanticCustomError(
                "invalid_url", "Enter an absolute http(s) URL, like https://example.com/page."
            )
        return value

    @field_validator("description")
    @classmethod
    def blank_description_is_none(cls, value: str | None) -> str | None:
        stripped = value.strip() if value is not None else ""
        return stripped or None


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    target_url: str
    description: str | None
    visit_count: int
    last_visited_at: AwareDatetime | None
    created_at: AwareDatetime


class LinkList(BaseModel):
    items: list[LinkOut]


class Health(BaseModel):
    status: Literal["ok"]


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
