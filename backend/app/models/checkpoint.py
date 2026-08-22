"""Pipeline checkpoint model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String

from . import Base  # type: ignore


class PipelineCheckpoint(Base):  # type: ignore
    """Pipeline stage checkpoint model."""

    __tablename__ = "pipeline_checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    stage_name = Column(String(50), nullable=False, unique=True)
    completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return string representation of the checkpoint."""
        return f"<PipelineCheckpoint(stage={self.stage_name},\
          completed_at={self.completed_at})>"
