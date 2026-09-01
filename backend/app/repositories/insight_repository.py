"""Insight repository with specialized queries."""

from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..models import Insight
from .base import BaseRepository


class InsightRepository(BaseRepository[Insight]):
    """Repository for Insight entity."""

    def __init__(self, session: Session):
        """Initialize repository with session."""
        super().__init__(session, Insight)

    def create_insight(
        self,
        content: str,
        event_ids: List[str],
        stages: Optional[Dict[str, Any]] = None,
    ) -> Insight:
        """
        Create a new insight.

        Args:
            content: Generated insight content.
            event_ids: IDs of events used for generation.
            stages: Optional stages data (analyst, skeptic, synthesis).

        Returns:
            Created insight.

        """
        insight = Insight(
            content=content,
            event_ids=event_ids,
            event_count=len(event_ids),
            stages=stages,
        )
        self.add(insight)
        return insight

    def get_latest(self, limit: int = 10) -> List[Insight]:
        """
        Get latest insights.

        Args:
            limit: Maximum number of insights.

        Returns:
            List of insights sorted by created_at descending.

        """
        stmt = select(Insight).order_by(desc(Insight.created_at)).limit(limit)
        return list(self._session.scalars(stmt).all())

    def get_by_id_with_events(self, insight_id: str) -> Optional[Insight]:
        """Get insight by ID."""
        return self.get_by_id(insight_id)

    def delete_old_insights(self, keep_count: int = 100) -> int:
        """
        Delete oldest insights, keeping only the most recent ones.

        Args:
            keep_count: Number of recent insights to keep.

        Returns:
            Number of deleted insights.

        """
        stmt = select(Insight).order_by(Insight.created_at).offset(keep_count)
        old_insights = list(self._session.scalars(stmt).all())
        count = len(old_insights)
        for insight in old_insights:
            self.delete(insight)
        return count
