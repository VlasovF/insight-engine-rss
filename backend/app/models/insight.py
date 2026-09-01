"""Insight model for generated dialectical synthesis."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from . import Base  # type: ignore


class Insight(Base):  # type: ignore
    """Generated insight model."""

    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    event_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    event_count: Mapped[int] = mapped_column(nullable=False, default=0)
    stages: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # analyst, skeptic, synthesis
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        """Return string representation of the insight."""
        return f"<Insight(id={self.id}, event_count={self.event_count},\
            created_at={self.created_at})>"

    def to_dict(self) -> dict:
        """Convert insight to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "event_ids": self.event_ids,
            "event_count": self.event_count,
            "stages": self.stages,
            "created_at": self.created_at.isoformat(),
        }
