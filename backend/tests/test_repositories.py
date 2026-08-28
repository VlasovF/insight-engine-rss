"""Tests for repositories."""

import pytest

from app.models import CheckpointStage, Event, PipelineCheckpoint


class TestEventRepository:
    """Test EventRepository."""

    def test_add_event(self, uow):
        """Test adding an event."""
        event = Event(
            title="Test",
            content="Test content",
            content_hash="hash1",
        )
        uow.events.add(event)
        uow.commit()

        saved = uow.events.get_by_id(event.id)
        assert saved is not None
        assert saved.title == "Test"

    def test_get_by_hash(self, uow):
        """Test getting event by content hash."""
        event = Event(
            title="Test",
            content="Test content",
            content_hash="unique_hash",
        )
        uow.events.add(event)
        uow.commit()

        found = uow.events.get_by_hash("unique_hash")
        assert found is not None
        assert found.id == event.id

        not_found = uow.events.get_by_hash("nonexistent")
        assert not_found is None

    def test_get_by_status(self, uow):
        """Test getting events by status."""
        event1 = Event(
            title="Pending 1", content="c1", content_hash="h1", status="pending"
        )
        event2 = Event(
            title="Pending 2", content="c2", content_hash="h2", status="pending"
        )
        event3 = Event(
            title="Embedded", content="c3", content_hash="h3", status="embedded"
        )

        uow.events.add(event1)
        uow.events.add(event2)
        uow.events.add(event3)
        uow.commit()

        pending = uow.events.get_by_status("pending")
        assert len(pending) == 2
        assert all(e.status == "pending" for e in pending)

        embedded = uow.events.get_by_status("embedded")
        assert len(embedded) == 1
        assert embedded[0].title == "Embedded"

    def test_get_pending(self, uow):
        """Test get_pending helper."""
        event1 = Event(
            title="Pending", content="c1", content_hash="h1", status="pending"
        )
        event2 = Event(
            title="Embedded", content="c2", content_hash="h2", status="embedded"
        )

        uow.events.add(event1)
        uow.events.add(event2)
        uow.commit()

        pending = uow.events.get_pending()
        assert len(pending) == 1
        assert pending[0].status == "pending"

    def test_update_status(self, uow):
        """Test updating event status."""
        event = Event(
            title="Test",
            content="Test content",
            content_hash="hash123",
            status="pending",
        )
        uow.events.add(event)
        uow.commit()

        updated = uow.events.update_status(event.id, "embedded")
        assert updated is not None
        assert updated.status == "embedded"

        # Verify in DB
        saved = uow.events.get_by_id(event.id)
        assert saved.status == "embedded"

    def test_mark_duplicate(self, uow):
        """Test marking event as duplicate."""
        event = Event(
            title="Test",
            content="Test content",
            content_hash="hash456",
            status="pending",
        )
        uow.events.add(event)
        uow.commit()

        marked = uow.events.mark_duplicate(event.id)
        assert marked is not None
        assert marked.is_duplicate is True
        assert marked.status == "embedded"

    def test_count_by_status(self, uow):
        """Test counting events by status."""
        uow.events.add(
            Event(title="P1", content="c1", content_hash="h1", status="pending")
        )
        uow.events.add(
            Event(title="P2", content="c2", content_hash="h2", status="pending")
        )
        uow.events.add(
            Event(title="E1", content="c3", content_hash="h3", status="embedded")
        )
        uow.events.add(
            Event(title="E2", content="c4", content_hash="h4", status="embedded")
        )
        uow.events.add(
            Event(title="EV1", content="c5", content_hash="h5", status="evaluated")
        )
        uow.commit()

        counts = uow.events.count_by_status()
        assert counts["pending"] == 2
        assert counts["embedded"] == 2
        assert counts["evaluated"] == 1

    def test_reset_from_stage(self, uow):
        """Test resetting events from stage."""
        event1 = Event(
            title="E1",
            content="c1",
            content_hash="h1",
            status="embedded",
            is_duplicate=True,
        )
        event2 = Event(
            title="E2",
            content="c2",
            content_hash="h2",
            status="evaluated",
            evaluation_data={"test": 1},
        )
        uow.events.add(event1)
        uow.events.add(event2)
        uow.commit()

        # Reset to embedding
        count = uow.events.reset_from_stage("embedding")
        assert count == 2

        # Check first event
        e1 = uow.events.get_by_id(event1.id)
        assert e1.status == "pending"
        assert e1.is_duplicate is False

        # Check second event
        e2 = uow.events.get_by_id(event2.id)
        assert e2.status == "pending"
        assert e2.is_duplicate is False
        assert e2.evaluation_data is None

    def test_delete_all(self, uow):
        """Test deleting all events."""
        uow.events.add(Event(title="T1", content="c1", content_hash="h1"))
        uow.events.add(Event(title="T2", content="c2", content_hash="h2"))
        uow.commit()

        all_events = uow.events.get_all()
        assert len(all_events) == 2

        uow.events.delete_all()
        uow.commit()

        remaining = uow.events.get_all()
        assert len(remaining) == 0


class TestCheckpointRepository:
    """Test CheckpointRepository."""

    def test_add_checkpoint(self, uow):
        """Test adding a checkpoint."""
        checkpoint = PipelineCheckpoint(stage_name=CheckpointStage.EMBEDDING_COMPLETED)
        uow.checkpoints.add(checkpoint)
        uow.commit()

        saved = uow.checkpoints.get_by_id(checkpoint.id)
        assert saved is not None
        assert saved.stage_name == CheckpointStage.EMBEDDING_COMPLETED

    def test_get_by_stage(self, uow):
        """Test getting checkpoint by stage name."""
        checkpoint = PipelineCheckpoint(stage_name=CheckpointStage.EMBEDDING_COMPLETED)
        uow.checkpoints.add(checkpoint)
        uow.commit()

        found = uow.checkpoints.get_by_stage(CheckpointStage.EMBEDDING_COMPLETED)
        assert found is not None
        assert found.id == checkpoint.id

        with pytest.raises(ValueError):
            uow.checkpoints.get_by_stage("nonexistent")

    def test_get_or_create_existing(self, uow):
        """Test get_or_create with existing checkpoint."""
        checkpoint = PipelineCheckpoint(stage_name=CheckpointStage.EMBEDDING_COMPLETED)
        uow.checkpoints.add(checkpoint)
        uow.commit()

        result = uow.checkpoints.get_or_create(CheckpointStage.EMBEDDING_COMPLETED)
        assert result.id == checkpoint.id

    def test_get_or_create_new(self, uow):
        """Test get_or_create with new checkpoint."""
        result = uow.checkpoints.get_or_create(CheckpointStage.EMBEDDING_COMPLETED)
        uow.commit()

        assert result.id is not None
        assert result.stage_name == CheckpointStage.EMBEDDING_COMPLETED

        # Verify in DB
        saved = uow.checkpoints.get_by_stage(CheckpointStage.EMBEDDING_COMPLETED)
        assert saved is not None

    def test_mark_completed(self, uow):
        """Test marking stage as completed."""
        result = uow.checkpoints.mark_completed(CheckpointStage.EMBEDDING_COMPLETED)
        uow.commit()

        assert result.stage_name == CheckpointStage.EMBEDDING_COMPLETED

        saved = uow.checkpoints.get_by_stage(CheckpointStage.EMBEDDING_COMPLETED)
        assert saved is not None

    def test_delete_by_stage(self, uow):
        """Test deleting checkpoint by stage."""
        checkpoint = PipelineCheckpoint(stage_name=CheckpointStage.EMBEDDING_COMPLETED)
        uow.checkpoints.add(checkpoint)
        uow.commit()

        uow.checkpoints.delete_by_stage(CheckpointStage.EMBEDDING_COMPLETED)
        uow.commit()

        deleted = uow.checkpoints.get_by_stage(CheckpointStage.EMBEDDING_COMPLETED)
        assert deleted is None

    def test_is_stage_completed(self, uow):
        """Test checking if stage is completed."""
        assert (
            uow.checkpoints.is_stage_completed(CheckpointStage.EMBEDDING_COMPLETED)
            is False
        )

        uow.checkpoints.mark_completed(CheckpointStage.EMBEDDING_COMPLETED)
        uow.commit()

        assert (
            uow.checkpoints.is_stage_completed(CheckpointStage.EMBEDDING_COMPLETED)
            is True
        )

    def test_get_pipeline_progress(self, uow):
        """Test getting pipeline progress."""
        # Initially no checkpoints
        progress = uow.checkpoints.get_pipeline_progress()
        assert progress["completed_stages"] == []
        assert progress["percentage"] == 0

        # Add a checkpoint
        uow.checkpoints.mark_completed(CheckpointStage.EMBEDDING_COMPLETED)
        uow.commit()

        progress = uow.checkpoints.get_pipeline_progress()
        assert CheckpointStage.EMBEDDING_COMPLETED in progress["completed_stages"]
        assert progress["percentage"] == 33  # 1 of 3 stages

    def test_get_completed_checkpoints(self, uow):
        """Test getting all completed checkpoints."""
        uow.checkpoints.mark_completed(
            CheckpointStage.EMBEDDING_COMPLETED, metadata={"processed": 10}
        )
        uow.commit()

        checkpoints = uow.checkpoints.get_completed_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0]["stage_name"] == CheckpointStage.EMBEDDING_COMPLETED
        assert checkpoints[0]["metadata"]["processed"] == 10
