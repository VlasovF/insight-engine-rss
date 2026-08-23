"""Base repository with common CRUD operations."""

from typing import Any, Generic, List, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository providing common database operations."""

    def __init__(self, session: Session, model_class: Any):
        """Initialize repository with session and model class."""
        self._session = session
        self._model_class = model_class

    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        return self._session.get(self._model_class, id)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination."""
        stmt = select(self._model_class).limit(limit).offset(offset)
        return list(self._session.scalars(stmt).all())

    def add(self, entity: T) -> T:
        """Add entity to session."""
        self._session.add(entity)
        return entity

    def delete(self, entity: T) -> None:
        """Delete entity from session."""
        self._session.delete(entity)

    def delete_all(self) -> None:
        """Delete all entities."""
        self._session.query(self._model_class).delete()
