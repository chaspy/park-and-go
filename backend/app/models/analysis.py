from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

from sqlalchemy import ForeignKey, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"))
    verdict: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    vehicle_fit: Mapped[str] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text)
    raw_result_json: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(default=_utcnow)

    place: Mapped["Place"] = relationship(back_populates="analyses")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="analysis")
    nearby_parkings: Mapped[list["NearbyParking"]] = relationship(back_populates="analysis")
