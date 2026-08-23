"""Tests for Events API endpoints."""

from app.models import Event


class TestEventsAPI:
    """Test Events API endpoints."""

    def test_get_events_empty(self, client):
        """Test getting events when none exist."""
        response = client.get("/api/events/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_events_with_data(self, client, db_session):
        """Test getting events with data."""
        # Create test events using db_session directly
        event1 = Event(
            title="Event 1",
            content="Content 1",
            content_hash="hash1",
            status="pending",
        )
        event2 = Event(
            title="Event 2",
            content="Content 2",
            content_hash="hash2",
            status="embedded",
        )
        db_session.add(event1)
        db_session.add(event2)
        db_session.commit()

        response = client.get("/api/events/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

        titles = [item["title"] for item in data["items"]]
        assert "Event 1" in titles
        assert "Event 2" in titles

    def test_get_events_filter_by_status(self, client, db_session):
        """Test filtering events by status."""
        event1 = Event(
            title="Pending 1",
            content="Content 1",
            content_hash="hash1",
            status="pending",
        )
        event2 = Event(
            title="Pending 2",
            content="Content 2",
            content_hash="hash2",
            status="pending",
        )
        event3 = Event(
            title="Embedded 1",
            content="Content 3",
            content_hash="hash3",
            status="embedded",
        )
        db_session.add(event1)
        db_session.add(event2)
        db_session.add(event3)
        db_session.commit()

        response = client.get("/api/events/?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert all(item["status"] == "pending" for item in data["items"])

    def test_get_events_filter_by_duplicate(self, client, db_session):
        """Test filtering events by duplicate status."""
        event1 = Event(
            title="Duplicate 1",
            content="Content 1",
            content_hash="hash1",
            is_duplicate=True,
        )
        event2 = Event(
            title="Unique 1",
            content="Content 2",
            content_hash="hash2",
            is_duplicate=False,
        )
        db_session.add(event1)
        db_session.add(event2)
        db_session.commit()

        response = client.get("/api/events/?is_duplicate=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["is_duplicate"] is True

    def test_get_events_pagination(self, client, db_session):
        """Test pagination with limit and offset."""
        for i in range(10):
            event = Event(
                title=f"Event {i}",
                content=f"Content {i}",
                content_hash=f"hash{i}",
            )
            db_session.add(event)
        db_session.commit()

        response = client.get("/api/events/?limit=3&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 10

    def test_delete_all_events(self, client, db_session):
        """Test deleting all events."""
        event1 = Event(
            title="To Delete 1",
            content="Content 1",
            content_hash="hash1",
        )
        event2 = Event(
            title="To Delete 2",
            content="Content 2",
            content_hash="hash2",
        )
        db_session.add(event1)
        db_session.add(event2)
        db_session.commit()

        # Verify events exist
        response = client.get("/api/events/")
        assert response.status_code == 200
        assert response.json()["total"] == 2

        # Delete all
        response = client.delete("/api/events/")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2

        # Verify events are gone
        response = client.get("/api/events/")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_delete_all_events_empty(self, client, db_session):
        """Test deleting all events when none exist."""
        response = client.delete("/api/events/")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
