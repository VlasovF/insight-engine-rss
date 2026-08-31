"""Tests for Unit of Work."""

import pytest

from app.models import CheckpointStage, Event
from app.uow import UnitOfWork


class TestUnitOfWork:
    """Test Unit of Work pattern."""

    def test_uow_initialization(self, uow):
        """Test UnitOfWork initialization."""
        assert uow.events is not None
        assert uow.checkpoints is not None

    def test_uow_commit(self, uow):
        """Test committing transaction."""
        event = Event(
            title="Test",
            content="Test content",
            content_hash="hash123",
        )
        uow.events.add(event)
        uow.commit()

        saved = uow.events.get_by_id(event.id)
        assert saved is not None

    def test_uow_rollback(self, db_session):
        """Test rolling back transaction."""

        class TestSessionFactory:
            def __call__(self):
                return db_session

        uow = UnitOfWork(TestSessionFactory())

        try:
            with uow.begin() as transaction:
                event = Event(
                    title="Test",
                    content="Test content",
                    content_hash="hash123",
                )
                transaction.events.add(event)
                raise ValueError("Test rollback")
        except ValueError:
            pass

        with db_session.begin():
            count = db_session.query(Event).count()
            assert count == 0

    def test_uow_context_manager(self, db_session):
        """Test UnitOfWork as context manager."""

        class TestSessionFactory:
            def __call__(self):
                return db_session

        uow = UnitOfWork(TestSessionFactory())

        with uow.begin() as transaction:
            event = Event(
                title="Test",
                content="Test content",
                content_hash="hash123",
            )
            transaction.events.add(event)

        with db_session.begin():
            count = db_session.query(Event).count()
            assert count == 1

    def test_uow_property_error(self):
        """Test error when accessing repositories without initialization."""
        uow = UnitOfWork(None)
        with pytest.raises(RuntimeError, match="UnitOfWork not initialized"):
            _ = uow.events

    def test_uow_events_repository(self, uow):
        """Test events repository is accessible."""
        assert uow.events is not None
        assert hasattr(uow.events, "add")
        assert hasattr(uow.events, "get_by_id")

    def test_uow_checkpoints_repository(self, uow):
        """Test checkpoints repository is accessible."""
        assert uow.checkpoints is not None
        assert hasattr(uow.checkpoints, "create_checkpoint")
        assert hasattr(uow.checkpoints, "get_last_checkpoint")
        assert hasattr(uow.checkpoints, "get_checkpoints")

    def test_uow_multiple_operations(self, uow):
        """Test multiple operations in one transaction."""
        event1 = Event(title="E1", content="c1", content_hash="h1")
        event2 = Event(title="E2", content="c2", content_hash="h2")
        uow.events.add(event1)
        uow.events.add(event2)
        uow.commit()

        all_events = uow.events.get_all()
        assert len(all_events) == 2

    def test_uow_checkpoint_operations(self, uow):
        """Test checkpoint operations in transaction."""
        checkpoint = uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1", "evt2"],
        )
        uow.commit()

        saved = uow.checkpoints.get_by_id(checkpoint.id)
        assert saved is not None
        assert saved.stage_name == CheckpointStage.EMBEDDING_COMPLETED
        assert saved.event_count == 2
