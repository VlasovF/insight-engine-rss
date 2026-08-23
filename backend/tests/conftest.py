"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base
from app.uow import UnitOfWork


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a temporary database session for testing."""
    # Create temporary database file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create engine
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa N806
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        # Clean up temporary file
        if Path(path).exists():
            Path(path).unlink()


@pytest.fixture(scope="function")
def uow(db_session: Session) -> Generator[UnitOfWork, None, None]:
    """Create a UnitOfWork instance for testing."""

    class TestSessionFactory:
        def __call__(self):
            return db_session

    uow = UnitOfWork(TestSessionFactory())
    with uow.begin() as transaction:
        yield transaction
