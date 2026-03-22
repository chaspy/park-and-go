from sqlalchemy import ForeignKey, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    source: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    raw_json: Mapped[str | None] = mapped_column(Text)

    analysis: Mapped["Analysis"] = relationship(back_populates="evidences")
