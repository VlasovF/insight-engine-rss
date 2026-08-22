"""Event model for news items."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text

from . import Base  # type: ignore


class Event(Base):  # type: ignore
    """News event model."""

    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(512), nullable=True)
    published_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    is_duplicate = Column(Boolean, nullable=False, default=False)
    content_hash = Column(String(64), nullable=False, unique=True)
    evaluation_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """Return string representation of the event."""
        return f"<Event(id={self.id}, title={self.title[:30]}...,\
              status={self.status})>"
