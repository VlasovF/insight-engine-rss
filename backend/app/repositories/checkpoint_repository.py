"""Checkpoint repository with specialized queries."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CheckpointStage, PipelineCheckpoint
from .base import BaseRepository


class CheckpointRepository(BaseRepository[PipelineCheckpoint]):
    """Repository for PipelineCheckpoint entity."""

    def __init__(self, session: Session):
        """Initialize repository with session."""
        super().__init__(session, PipelineCheckpoint)

    def get_by_stage(self, stage_name: str) -> Optional[PipelineCheckpoint]:
        """Get checkpoint by stage name."""
        if not CheckpointStage.is_valid(stage_name):
            raise ValueError(f"Invalid stage: {stage_name}")

        stmt = select(PipelineCheckpoint).where(
            PipelineCheckpoint.stage_name == stage_name
        )
        return self._session.scalar(stmt)

    def get_or_create(self, stage_name: str) -> PipelineCheckpoint:
        """Get checkpoint or create if not exists."""
        if not CheckpointStage.is_valid(stage_name):
            raise ValueError(f"Invalid stage: {stage_name}")

        checkpoint = self.get_by_stage(stage_name)
        if not checkpoint:
            checkpoint = PipelineCheckpoint(stage_name=stage_name)
            self.add(checkpoint)
        return checkpoint

    def mark_completed(
        self,
        stage_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineCheckpoint:
        """
        Mark stage as completed with optional metadata.

        Args:
            stage_name: Name of the stage.
            metadata: Additional metadata to store with checkpoint.

        Returns:
            The checkpoint instance.

        """
        if not CheckpointStage.is_valid(stage_name):
            raise ValueError(f"Invalid stage: {stage_name}")

        checkpoint = self.get_or_create(stage_name)
        if metadata:
            checkpoint.checkpoint_metadata = metadata
        checkpoint.completed_at = datetime.now(timezone.utc)
        return checkpoint

    def delete_by_stage(self, stage_name: str) -> None:
        """Delete checkpoint by stage."""
        if not CheckpointStage.is_valid(stage_name):
            raise ValueError(f"Invalid stage: {stage_name}")

        checkpoint = self.get_by_stage(stage_name)
        if checkpoint:
            self.delete(checkpoint)

    def get_all_stages(self) -> List[str]:
        """Get all completed stage names."""
        stmt = select(PipelineCheckpoint.stage_name)
        return list(self._session.scalars(stmt).all())

    def get_completed_checkpoints(self) -> List[Dict[str, Any]]:
        """Get all completed checkpoints as dictionaries."""
        stmt = select(PipelineCheckpoint)
        checkpoints = list(self._session.scalars(stmt).all())
        return [cp.to_dict() for cp in checkpoints]

    def is_stage_completed(self, stage_name: str) -> bool:
        """Check if a stage is completed."""
        checkpoint = self.get_by_stage(stage_name)
        return checkpoint is not None

    def get_last_completed_stage(self) -> Optional[str]:
        """Get the most recently completed stage."""
        stmt = (
            select(PipelineCheckpoint)
            .order_by(PipelineCheckpoint.completed_at.desc())
            .limit(1)
        )
        checkpoint = self._session.scalar(stmt)
        return checkpoint.stage_name if checkpoint else None

    def get_pipeline_progress(self) -> Dict[str, Any]:
        """
        Get overall pipeline progress.

        Returns:
            Dictionary with stage completion status and progress percentage.

        """
        stages = CheckpointStage.choices()
        completed = self.get_all_stages()

        progress = {stage: stage in completed for stage in stages}

        return {
            "completed_stages": completed,
            "progress": progress,
            "percentage": int(len(completed) / len(stages) * 100),
            "last_completed": self.get_last_completed_stage(),
        }
