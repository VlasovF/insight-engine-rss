"""Checkpoint repository with specialized queries."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..models import CheckpointStage, PipelineCheckpoint
from .base import BaseRepository


class CheckpointRepository(BaseRepository[PipelineCheckpoint]):
    """Repository for PipelineCheckpoint entity."""

    def __init__(self, session: Session):
        """Initialize repository with session."""
        super().__init__(session, PipelineCheckpoint)

    def _validate_stage(self, stage_name: str) -> None:
        """Validate stage name."""
        if not CheckpointStage.is_valid(stage_name):
            raise ValueError(f"Invalid stage: {stage_name}")

    def create_checkpoint(
        self,
        stage_name: str,
        event_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineCheckpoint:
        """
        Create a new checkpoint for a batch of events.

        Args:
            stage_name: Name of the stage.
            event_ids: List of event IDs in this batch.
            metadata: Additional metadata.

        Returns:
            The created checkpoint.

        """
        self._validate_stage(stage_name)

        checkpoint = PipelineCheckpoint(
            stage_name=stage_name,
            event_ids=event_ids,
            event_count=len(event_ids),
            checkpoint_metadata=metadata,
            completed_at=datetime.now(timezone.utc),
        )
        self.add(checkpoint)
        return checkpoint

    def get_last_checkpoint(self, stage_name: str) -> Optional[PipelineCheckpoint]:
        """
        Get the most recent checkpoint for a stage.

        Args:
            stage_name: Name of the stage.

        Returns:
            Most recent checkpoint or None.

        """
        self._validate_stage(stage_name)

        stmt = (
            select(PipelineCheckpoint)
            .where(PipelineCheckpoint.stage_name == stage_name)
            .order_by(desc(PipelineCheckpoint.completed_at))
            .limit(1)
        )
        return self._session.scalar(stmt)

    def get_checkpoints(
        self, stage_name: str, limit: int = 10
    ) -> List[PipelineCheckpoint]:
        """
        Get recent checkpoints for a stage.

        Args:
            stage_name: Name of the stage.
            limit: Maximum number of checkpoints.

        Returns:
            List of checkpoints.

        """
        self._validate_stage(stage_name)

        stmt = (
            select(PipelineCheckpoint)
            .where(PipelineCheckpoint.stage_name == stage_name)
            .order_by(desc(PipelineCheckpoint.completed_at))
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def get_processed_event_ids(self, stage_name: str) -> List[str]:
        """
        Get all event IDs that have been processed in a stage.

        Args:
            stage_name: Name of the stage.

        Returns:
            List of event IDs.

        """
        self._validate_stage(stage_name)

        checkpoints = self.get_checkpoints(stage_name, limit=1000)
        event_ids = []
        for cp in checkpoints:
            if cp.event_ids:
                event_ids.extend(cp.event_ids)
        return event_ids

    def get_unprocessed_event_ids(
        self,
        stage_name: str,
        all_event_ids: List[str],
    ) -> List[str]:
        """
        Get event IDs that have not been processed in a stage.

        Args:
            stage_name: Name of the stage.
            all_event_ids: All event IDs to check.

        Returns:
            List of unprocessed event IDs.

        """
        processed = set(self.get_processed_event_ids(stage_name))
        return [eid for eid in all_event_ids if eid not in processed]

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint by ID."""
        checkpoint = self.get_by_id(checkpoint_id)
        if checkpoint:
            self.delete(checkpoint)

    def delete_by_stage(self, stage_name: str) -> int:
        """Delete all checkpoints for a stage."""
        self._validate_stage(stage_name)

        stmt = select(PipelineCheckpoint).where(
            PipelineCheckpoint.stage_name == stage_name
        )
        checkpoints = list(self._session.scalars(stmt).all())
        count = len(checkpoints)
        for cp in checkpoints:
            self.delete(cp)
        return count

    def is_event_processed(self, stage_name: str, event_id: str) -> bool:
        """Check if an event has been processed in a stage."""
        processed = set(self.get_processed_event_ids(stage_name))
        return event_id in processed

    def get_pipeline_progress(self) -> Dict[str, Any]:
        """
        Get overall pipeline progress.

        Returns:
            Dictionary with stage completion status and progress percentage.

        """
        stages = CheckpointStage.choices()
        completed_stages = []

        for stage in stages:
            cp = self.get_last_checkpoint(stage)
            if cp:
                completed_stages.append(stage)

        total_stages = len(stages)
        completed = len(completed_stages)

        return {
            "completed_stages": completed_stages,
            "progress": {stage: stage in completed_stages for stage in stages},
            "percentage": int(completed / total_stages * 100)
            if total_stages > 0
            else 0,
            "last_completed": completed_stages[-1] if completed_stages else None,
        }

    def get_checkpoints_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all checkpoints.

        Returns:
            List of checkpoint summaries.

        """
        stages = CheckpointStage.choices()
        summary = []

        for stage in stages:
            checkpoints = self.get_checkpoints(stage, limit=5)
            for cp in checkpoints:
                summary.append(cp.to_dict())

        return sorted(summary, key=lambda x: x["completed_at"], reverse=True)
