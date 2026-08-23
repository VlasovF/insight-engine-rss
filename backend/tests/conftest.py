"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.dependencies import get_uow
from app.main import app
from app.models import Base
from app.uow import UnitOfWork


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a temporary database session for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # noqa N806
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
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


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a TestClient with test database dependency override."""

    def override_get_uow():
        class TestSessionFactory:
            def __call__(self):
                return db_session

        return UnitOfWork(TestSessionFactory())

    app.dependency_overrides[get_uow] = override_get_uow

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_feed_xml():
    """Sample RSS feed XML for testing."""
    return """
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Feed</title>
        <link>https://test.com</link>
        <description>Test RSS Feed</description>
        <item>
          <title>News Item 1</title>
          <link>https://test.com/1</link>
          <description>Description 1</description>
          <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
        </item>
        <item>
          <title>News Item 2</title>
          <link>https://test.com/2</link>
          <description>Description 2</description>
          <pubDate>Mon, 02 Jan 2024 12:00:00 +0000</pubDate>
        </item>
      </channel>
    </rss>
    """
