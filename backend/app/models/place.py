from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    place_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    place_id: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(String(1000))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    website_url: Mapped[str | None] = mapped_column(String(2000))
    raw_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=_utcnow, onupdate=_utcnow
    )

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="place")
