"""Pipeline checkpoint model."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base  # type: ignore


class PipelineCheckpoint(Base):  # type: ignore
    """Pipeline stage checkpoint model."""

    __tablename__ = "pipeline_checkpoints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    stage_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    completed_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        """Return string representation of the checkpoint."""
        return f"<PipelineCheckpoint(stage={self.stage_name},\
          completed_at={self.completed_at})>"
