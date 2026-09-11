from datetime import UTC, datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from golinks_api.db import Base, UTCDateTime


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    target_url: Mapped[str] = mapped_column(String(2048))
    description: Mapped[str | None] = mapped_column(String(280))
    visit_count: Mapped[int] = mapped_column(default=0)
    last_visited_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(UTC))
