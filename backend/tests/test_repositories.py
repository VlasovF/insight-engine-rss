"""Tests for repositories."""

from uuid import uuid4

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

        count = uow.events.reset_from_stage("embedding")
        assert count == 2

        e1 = uow.events.get_by_id(event1.id)
        assert e1.status == "pending"
        assert e1.is_duplicate is False

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
        event_ids = ["evt1", "evt2"]
        checkpoint = uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=event_ids,
        )
        uow.commit()

        assert checkpoint.id is not None
        assert checkpoint.stage_name == CheckpointStage.EMBEDDING_COMPLETED
        assert checkpoint.event_count == 2
        assert checkpoint.batch_id is not None

    def test_create_checkpoint_with_metadata(self, uow):
        """Test creating checkpoint with metadata."""
        event_ids = ["evt1", "evt2"]
        metadata = {"processed": 2, "errors": 0}

        checkpoint = uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=event_ids,
            metadata=metadata,
        )
        uow.commit()

        assert checkpoint.checkpoint_metadata == metadata

    def test_get_last_checkpoint(self, uow):
        """Test getting last checkpoint for a stage."""
        # Create first checkpoint
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1"],
        )
        uow.commit()

        # Create second checkpoint
        cp2 = uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt2", "evt3"],
        )
        uow.commit()

        last = uow.checkpoints.get_last_checkpoint(CheckpointStage.EMBEDDING_COMPLETED)
        assert last.id == cp2.id
        assert last.event_count == 2

    def test_get_checkpoints(self, uow):
        """Test getting recent checkpoints for a stage."""
        # Create multiple checkpoints with different batch_ids
        for i in range(3):
            checkpoint = PipelineCheckpoint(
                stage_name=CheckpointStage.EMBEDDING_COMPLETED,
                batch_id=str(uuid4()),
                event_ids=[f"evt{i}"],
                event_count=1,
            )
            uow.checkpoints.add(checkpoint)
        uow.commit()

        checkpoints = uow.checkpoints.get_checkpoints(
            CheckpointStage.EMBEDDING_COMPLETED, limit=2
        )
        assert len(checkpoints) == 2

    def test_get_processed_event_ids(self, uow):
        """Test getting processed event IDs."""
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1", "evt2"],
        )
        uow.commit()

        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt3"],
        )
        uow.commit()

        processed = uow.checkpoints.get_processed_event_ids(
            CheckpointStage.EMBEDDING_COMPLETED
        )
        assert set(processed) == {"evt1", "evt2", "evt3"}

    def test_get_unprocessed_event_ids(self, uow):
        """Test getting unprocessed event IDs."""
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1", "evt2"],
        )
        uow.commit()

        all_ids = ["evt1", "evt2", "evt3", "evt4"]
        unprocessed = uow.checkpoints.get_unprocessed_event_ids(
            CheckpointStage.EMBEDDING_COMPLETED,
            all_ids,
        )
        assert set(unprocessed) == {"evt3", "evt4"}

    def test_delete_checkpoint(self, uow):
        """Test deleting a checkpoint by ID."""
        checkpoint = uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1"],
        )
        uow.commit()

        uow.checkpoints.delete_checkpoint(checkpoint.id)
        uow.commit()

        deleted = uow.checkpoints.get_by_id(checkpoint.id)
        assert deleted is None

    def test_delete_by_stage(self, uow):
        """Test deleting all checkpoints for a stage."""
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1"],
        )
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EVALUATION_COMPLETED,
            event_ids=["evt2"],
        )
        uow.commit()

        count = uow.checkpoints.delete_by_stage(CheckpointStage.EMBEDDING_COMPLETED)
        assert count == 1

        remaining = uow.checkpoints.get_checkpoints(
            CheckpointStage.EVALUATION_COMPLETED, limit=10
        )
        assert len(remaining) == 1

    def test_is_event_processed(self, uow):
        """Test checking if event is processed."""
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1", "evt2"],
        )
        uow.commit()

        assert (
            uow.checkpoints.is_event_processed(
                CheckpointStage.EMBEDDING_COMPLETED, "evt1"
            )
            is True
        )
        assert (
            uow.checkpoints.is_event_processed(
                CheckpointStage.EMBEDDING_COMPLETED, "evt3"
            )
            is False
        )

    def test_get_pipeline_progress(self, uow):
        """Test getting pipeline progress."""
        progress = uow.checkpoints.get_pipeline_progress()
        assert progress["completed_stages"] == []
        assert progress["percentage"] == 0

        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1"],
        )
        uow.commit()

        progress = uow.checkpoints.get_pipeline_progress()
        assert CheckpointStage.EMBEDDING_COMPLETED in progress["completed_stages"]
        assert progress["percentage"] == 33

    def test_get_checkpoints_summary(self, uow):
        """Test getting checkpoints summary."""
        uow.checkpoints.create_checkpoint(
            stage_name=CheckpointStage.EMBEDDING_COMPLETED,
            event_ids=["evt1", "evt2"],
            metadata={"processed": 2},
        )
        uow.commit()

        summary = uow.checkpoints.get_checkpoints_summary()
        assert len(summary) == 1
        assert summary[0]["stage_name"] == CheckpointStage.EMBEDDING_COMPLETED
        assert summary[0]["event_count"] == 2
        assert summary[0]["metadata"]["processed"] == 2
