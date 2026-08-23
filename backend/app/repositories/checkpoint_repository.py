"""Checkpoint repository with specialized queries."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import PipelineCheckpoint
from .base import BaseRepository


class CheckpointRepository(BaseRepository[PipelineCheckpoint]):
    """Repository for PipelineCheckpoint entity."""

    def __init__(self, session: Session):
        """Initialize repository with session."""
        super().__init__(session, PipelineCheckpoint)

    def get_by_stage(self, stage_name: str) -> Optional[PipelineCheckpoint]:
        """Get checkpoint by stage name."""
        stmt = select(PipelineCheckpoint).where(
            PipelineCheckpoint.stage_name == stage_name
        )
        return self._session.scalar(stmt)

    def get_or_create(self, stage_name: str) -> PipelineCheckpoint:
        """Get checkpoint or create if not exists."""
        checkpoint = self.get_by_stage(stage_name)
        if not checkpoint:
            checkpoint = PipelineCheckpoint(stage_name=stage_name)
            self.add(checkpoint)
        return checkpoint

    def mark_completed(self, stage_name: str) -> PipelineCheckpoint:
        """Mark stage as completed."""
        checkpoint = self.get_or_create(stage_name)
        return checkpoint

    def delete_by_stage(self, stage_name: str) -> None:
        """Delete checkpoint by stage."""
        checkpoint = self.get_by_stage(stage_name)
        if checkpoint:
            self.delete(checkpoint)
