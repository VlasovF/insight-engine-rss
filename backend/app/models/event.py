"""Event model for news items."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from . import Base  # type: ignore


class EventStatus:
    """Event status constants."""

    PENDING = "pending"
    EMBEDDED = "embedded"
    EVALUATED = "evaluated"

    @classmethod
    def choices(cls) -> list:
        """Get all status choices."""
        return [cls.PENDING, cls.EMBEDDED, cls.EVALUATED]

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if status is valid."""
        return status in cls.choices()


class Event(Base):  # type: ignore
    """News event model."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    evaluation_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        """Return string representation of the event."""
        return f"<Event(id={self.id}, title={self.title[:30]}...,\
              status={self.status})>"

    def transition_to(self, new_status: str) -> None:
        """
        Transition event to a new status.

        Args:
            new_status: Target status.

        Raises:
            ValueError: If transition is invalid.

        """
        valid_transitions = {
            EventStatus.PENDING: [EventStatus.EMBEDDED],
            EventStatus.EMBEDDED: [EventStatus.EVALUATED],
            EventStatus.EVALUATED: [],
        }

        allowed = valid_transitions.get(self.status, [])
        if new_status not in allowed and new_status != self.status:
            raise ValueError(
                f"Invalid status transition: {self.status} -> {new_status}. "
                f"Allowed: {allowed}"
            )

        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def mark_embedded(self) -> None:
        """Mark event as embedded."""
        self.transition_to(EventStatus.EMBEDDED)

    def mark_evaluated(self) -> None:
        """Mark event as evaluated."""
        self.transition_to(EventStatus.EVALUATED)

    def reset_to_pending(self) -> None:
        """Reset event to pending status."""
        self.status = EventStatus.PENDING
        self.is_duplicate = False
        self.evaluation_data = None
        self.updated_at = datetime.now(timezone.utc)

    def reset_to_embedded(self) -> None:
        """Reset event to embedded status (keep embedding, remove evaluation)."""
        self.status = EventStatus.EMBEDDED
        self.evaluation_data = None
        self.updated_at = datetime.now(timezone.utc)
