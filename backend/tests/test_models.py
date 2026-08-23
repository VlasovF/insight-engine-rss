"""Tests for SQLAlchemy models."""

from datetime import datetime

from app.models import Event, PipelineCheckpoint


class TestEventModel:
    """Test Event model."""

    def test_create_event(self, db_session):
        """Test creating an event."""
        event = Event(
            title="Test News",
            content="Test content",
            source_url="https://test.com",
            content_hash="hash123",
        )
        db_session.add(event)
        db_session.commit()

        assert event.id is not None
        assert event.status == "pending"
        assert event.is_duplicate is False
        assert event.created_at is not None
        assert event.updated_at is not None
        assert isinstance(event.created_at, datetime)

    def test_event_repr(self, db_session):
        """Test Event string representation."""
        event = Event(
            title="Short Title",
            content="Test content",
            content_hash="hash123",
        )
        db_session.add(event)
        db_session.commit()

        repr_str = repr(event)
        assert "Event" in repr_str
        assert "Short Title" in repr_str
        assert "pending" in repr_str

    def test_event_status_default(self, db_session):
        """Test default status is 'pending'."""
        event = Event(
            title="Test",
            content="Test",
            content_hash="hash456",
        )
        db_session.add(event)
        db_session.commit()

        assert event.status == "pending"

    def test_event_content_hash_unique(self, db_session):
        """Test content_hash is unique."""
        event1 = Event(
            title="Test 1",
            content="Same content",
            content_hash="samehash",
        )
        event2 = Event(
            title="Test 2",
            content="Same content",
            content_hash="samehash",
        )
        db_session.add(event1)
        db_session.commit()

        import pytest
        from sqlalchemy.exc import IntegrityError

        db_session.add(event2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_event_evaluation_data_json(self, db_session):
        """Test evaluation_data stores JSON."""
        event = Event(
            title="Test",
            content="Test",
            content_hash="hash789",
            evaluation_data={"surprise": 0.8, "conflict": 0.5},
        )
        db_session.add(event)
        db_session.commit()

        assert event.evaluation_data is not None
        assert event.evaluation_data["surprise"] == 0.8
        assert event.evaluation_data["conflict"] == 0.5


class TestPipelineCheckpointModel:
    """Test PipelineCheckpoint model."""

    def test_create_checkpoint(self, db_session):
        """Test creating a checkpoint."""
        checkpoint = PipelineCheckpoint(
            stage_name="embedding_completed",
        )
        db_session.add(checkpoint)
        db_session.commit()

        assert checkpoint.id is not None
        assert checkpoint.stage_name == "embedding_completed"
        assert checkpoint.completed_at is not None

    def test_checkpoint_stage_name_unique(self, db_session):
        """Test stage_name is unique."""
        cp1 = PipelineCheckpoint(stage_name="embedding_completed")
        cp2 = PipelineCheckpoint(stage_name="embedding_completed")
        db_session.add(cp1)
        db_session.commit()

        import pytest
        from sqlalchemy.exc import IntegrityError

        db_session.add(cp2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_checkpoint_repr(self, db_session):
        """Test PipelineCheckpoint string representation."""
        checkpoint = PipelineCheckpoint(stage_name="evaluation_completed")
        db_session.add(checkpoint)
        db_session.commit()

        repr_str = repr(checkpoint)
        assert "PipelineCheckpoint" in repr_str
        assert "evaluation_completed" in repr_str
