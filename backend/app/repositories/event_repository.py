"""Event repository with specialized queries."""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Event, EventStatus
from .base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for Event entity with specialized queries."""

    def __init__(self, session: Session):
        """Initialize repository with session."""
        super().__init__(session, Event)

    def get_by_hash(self, content_hash: str) -> Optional[Event]:
        """Get event by content hash."""
        stmt = select(Event).where(Event.content_hash == content_hash)
        return self._session.scalar(stmt)

    def get_by_status(self, status: str, limit: int = 100) -> List[Event]:
        """Get events by status."""
        if not EventStatus.is_valid(status):
            raise ValueError(f"Invalid status: {status}")
        stmt = select(Event).where(Event.status == status).limit(limit)
        return list(self._session.scalars(stmt).all())

    def get_pending(self, limit: int = 100) -> List[Event]:
        """Get pending events."""
        return self.get_by_status(EventStatus.PENDING, limit)

    def get_embedded(self, limit: int = 100) -> List[Event]:
        """Get embedded events."""
        return self.get_by_status(EventStatus.EMBEDDED, limit)

    def get_evaluated(self, limit: int = 100) -> List[Event]:
        """Get evaluated events."""
        return self.get_by_status(EventStatus.EVALUATED, limit)

    def get_non_duplicates(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Event]:
        """Get non-duplicate events."""
        stmt = select(Event).where(Event.is_duplicate == False)  # noqa E712
        if status:
            if not EventStatus.is_valid(status):
                raise ValueError(f"Invalid status: {status}")
            stmt = stmt.where(Event.status == status)
        stmt = stmt.limit(limit)
        return list(self._session.scalars(stmt).all())

    def update_status(self, event_id: str, status: str) -> Optional[Event]:
        """Update event status with validation."""
        if not EventStatus.is_valid(status):
            raise ValueError(f"Invalid status: {status}")

        event = self.get_by_id(event_id)
        if event:
            event.transition_to(status)
        return event

    def mark_duplicate(self, event_id: str) -> Optional[Event]:
        """Mark event as duplicate and set status to embedded."""
        event = self.get_by_id(event_id)
        if event:
            event.is_duplicate = True
            event.status = EventStatus.EMBEDDED
            event.updated_at = event.updated_at  # Refresh
        return event

    def reset_from_stage(self, stage: str) -> int:
        """
        Reset events status to specified stage.

        Args:
            stage: Target stage ("embedding" or "evaluation").

        Returns:
            Number of events reset.

        """
        stage_map = {
            "embedding": EventStatus.PENDING,
            "evaluation": EventStatus.EMBEDDED,
        }
        target_status = stage_map.get(stage)
        if not target_status:
            return 0

        events = self._session.query(Event).all()
        count = 0

        for event in events:
            if stage == "embedding":
                event.reset_to_pending()
            elif stage == "evaluation":
                event.reset_to_embedded()
            count += 1

        return count

    def count_by_status(self) -> dict:
        """Count events by status."""
        result = {}
        for status in EventStatus.choices():
            stmt = select(func.count()).select_from(Event).where(Event.status == status)
            result[status] = self._session.scalar(stmt) or 0
        return result
