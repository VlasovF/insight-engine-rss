"""Dependency injection for FastAPI."""

from .database import SessionLocal
from .uow import UnitOfWork


def get_uow() -> UnitOfWork:
    """Dependency injection for Unit of Work."""
    return UnitOfWork(SessionLocal)
