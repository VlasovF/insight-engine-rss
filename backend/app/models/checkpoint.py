"""Pipeline checkpoint model."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base  # type: ignore


class CheckpointStage:
    """Checkpoint stage constants."""

    EMBEDDING_COMPLETED = "embedding_completed"
    EVALUATION_COMPLETED = "evaluation_completed"
    INSIGHT_GENERATED = "insight_generated"

    @classmethod
    def choices(cls) -> list:
        """Get all checkpoint stages."""
        return [
            cls.EMBEDDING_COMPLETED,
            cls.EVALUATION_COMPLETED,
            cls.INSIGHT_GENERATED,
        ]

    @classmethod
    def is_valid(cls, stage: str) -> bool:
        """Check if stage is valid."""
        return stage in cls.choices()


class PipelineCheckpoint(Base):  # type: ignore
    """Pipeline stage checkpoint model."""

    __tablename__ = "pipeline_checkpoints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    stage_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    completed_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    checkpoint_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        """Return string representation of the checkpoint."""
        return f"<PipelineCheckpoint(stage={self.stage_name},\
              completed_at={self.completed_at})>"

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary."""
        return {
            "id": self.id,
            "stage_name": self.stage_name,
            "completed_at": self.completed_at.isoformat(),
            "metadata": self.checkpoint_metadata,
        }
