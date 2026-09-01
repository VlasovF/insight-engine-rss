"""Unit of Work for managing database transactions."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from sqlalchemy.orm import Session

from ..repositories import CheckpointRepository, EventRepository, InsightRepository


class UnitOfWork:
    """Unit of Work managing database session and repositories."""

    def __init__(self, session_factory: Any):
        """Initialize Unit of Work with session factory."""
        self._session_factory = session_factory
        self._session: Optional[Session] = None
        self._events: Optional[EventRepository] = None
        self._checkpoints: Optional[CheckpointRepository] = None
        self._insights: Optional[InsightRepository] = None

    def __enter__(self) -> "UnitOfWork":
        """Enter context manager."""
        self._session = self._session_factory()
        self._events = EventRepository(self._session)
        self._checkpoints = CheckpointRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit context manager."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()

    @property
    def events(self) -> EventRepository:
        """Get EventRepository instance."""
        if self._events is None:
            raise RuntimeError("UnitOfWork not initialized. Use 'with' statement.")
        return self._events

    @property
    def checkpoints(self) -> CheckpointRepository:
        """Get CheckpointRepository instance."""
        if self._checkpoints is None:
            raise RuntimeError("UnitOfWork not initialized. Use 'with' statement.")
        return self._checkpoints

    @property
    def insights(self) -> InsightRepository:
        """Get InsightRepository instance."""
        if self._insights is None:
            raise RuntimeError("UnitOfWork not initialized. Use 'with' statement.")
        return self._insights

    def commit(self) -> None:
        """Commit transaction."""
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        """Rollback transaction."""
        if self._session:
            self._session.rollback()

    def close(self) -> None:
        """Close session."""
        if self._session:
            self._session.close()
            self._session = None
            self._events = None
            self._checkpoints = None
            self._insights = None

    @contextmanager
    def begin(self) -> Generator["UnitOfWork", None, None]:
        """Context manager for transaction."""
        with self:
            yield self
