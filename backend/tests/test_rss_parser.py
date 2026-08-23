"""Tests for RSS Parser service."""

from unittest.mock import Mock, patch

import httpx

from app.services import RSSParserService


class TestRSSParserService:
    """Test RSSParserService."""

    def test_extract_content_with_content_field(self, uow):
        """Test extracting content from feed entry."""
        parser = RSSParserService(uow.events)
        entry = {
            "title": "Test Title",
            "content": [{"value": "Test content body"}],
        }
        content = parser._extract_content(entry)
        assert content == "Test content body"

    def test_extract_content_with_summary_fallback(self, uow):
        """Test fallback to summary when content missing."""
        parser = RSSParserService(uow.events)
        entry = {
            "title": "Test Title",
            "summary": "Test summary",
        }
        content = parser._extract_content(entry)
        assert content == "Test summary"

    def test_extract_content_with_description_fallback(self, uow):
        """Test fallback to description when content and summary missing."""
        parser = RSSParserService(uow.events)
        entry = {
            "title": "Test Title",
            "description": "Test description",
        }
        content = parser._extract_content(entry)
        assert content == "Test description"

    def test_extract_content_fallback_to_title(self, uow):
        """Test fallback to title when all content fields missing."""
        parser = RSSParserService(uow.events)
        entry = {"title": "Test Title"}
        content = parser._extract_content(entry)
        assert content == "Test Title"

    def test_parse_published_date_valid(self, uow):
        """Test parsing valid published date."""
        parser = RSSParserService(uow.events)
        entry = {"published": "Mon, 01 Jan 2024 12:00:00 +0000"}
        dt = parser._parse_published_date(entry)
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_parse_published_date_fallback(self, uow):
        """Test fallback to current time when date parsing fails."""
        parser = RSSParserService(uow.events)
        entry = {"published": "invalid date"}
        dt = parser._parse_published_date(entry)
        assert dt is not None

    def test_save_entry_creates_event(self, uow):
        """Test saving entry creates new event."""
        parser = RSSParserService(uow.events)
        entry = {
            "title": "Test News",
            "content": [{"value": "Test content"}],
            "published": "Mon, 01 Jan 2024 12:00:00 +0000",
        }
        source_url = "https://test.com/rss"

        result = parser._save_entry(entry, source_url)
        uow.commit()
        assert result is True

        events = uow.events.get_all()
        assert len(events) == 1
        assert events[0].title == "Test News"

    def test_save_entry_skips_empty_content(self, uow):
        """Test skipping entry with empty content."""
        parser = RSSParserService(uow.events)
        entry = {"title": ""}
        source_url = "https://test.com/rss"

        result = parser._save_entry(entry, source_url)
        uow.commit()
        assert result is False

        events = uow.events.get_all()
        assert len(events) == 0

    def test_save_entry_detects_duplicate(self, uow):
        """Test duplicate detection."""
        parser = RSSParserService(uow.events)

        entry = {
            "title": "Test News",
            "content": [{"value": "Test content"}],
        }
        source_url = "https://test.com/rss"

        parser._save_entry(entry, source_url)
        uow.commit()

        result = parser._save_entry(entry, source_url)
        uow.commit()
        assert result is False

        events = uow.events.get_all()
        assert len(events) == 1

    def test_fetch_single_feed_success(self, uow):
        """Test fetching single feed successfully."""
        parser = RSSParserService(uow.events)

        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Test News 1</title>
              <description>Content 1</description>
            </item>
            <item>
              <title>Test News 2</title>
              <description>Content 2</description>
            </item>
          </channel>
        </rss>
        """

        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_xml
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = parser._fetch_single_feed("https://test.com/feed")
            uow.commit()

        assert result["fetched"] == 2
        assert result["new"] == 2
        assert result["error"] is None

        events = uow.events.get_all()
        assert len(events) == 2

    def test_fetch_single_feed_http_error(self, uow):
        """Test handling HTTP error."""
        parser = RSSParserService(uow.events)

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=Mock(status_code=404),
            )

            result = parser._fetch_single_feed("https://test.com/feed")

        assert result["fetched"] == 0
        assert result["new"] == 0
        assert result["error"] == "HTTP 404"

    def test_fetch_single_feed_timeout(self, uow):
        """Test handling timeout."""
        parser = RSSParserService(uow.events)

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            result = parser._fetch_single_feed("https://test.com/feed")

        assert result["fetched"] == 0
        assert result["new"] == 0
        assert result["error"] == "Request timeout"

    def test_fetch_feeds_multiple_urls(self, uow):
        """Test fetching multiple feeds."""
        parser = RSSParserService(uow.events)

        # Different content for each feed to avoid duplicate hashes
        mock_xml1 = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Feed 1 News</title>
              <description>Content from feed 1</description>
            </item>
          </channel>
        </rss>
        """

        mock_xml2 = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Feed 2 News</title>
              <description>Content from feed 2</description>
            </item>
          </channel>
        </rss>
        """

        with patch("httpx.get") as mock_get:
            mock_response1 = Mock()
            mock_response1.text = mock_xml1
            mock_response1.raise_for_status = Mock()

            mock_response2 = Mock()
            mock_response2.text = mock_xml2
            mock_response2.raise_for_status = Mock()

            mock_get.side_effect = [mock_response1, mock_response2]

            result = parser.fetch_feeds(
                [
                    "https://test.com/feed1",
                    "https://test.com/feed2",
                ]
            )
            uow.commit()

        assert result["total_fetched"] == 2
        assert result["total_new"] == 2
        assert result["errors"] == []

    def test_fetch_feeds_with_errors(self, uow):
        """Test fetching feeds with some errors."""
        parser = RSSParserService(uow.events)

        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Test News</title>
              <description>Content from feed</description>
            </item>
          </channel>
        </rss>
        """

        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_xml
            mock_response.raise_for_status = Mock()

            mock_get.side_effect = [
                mock_response,
                httpx.HTTPStatusError(
                    "404 Not Found",
                    request=Mock(),
                    response=Mock(status_code=404),
                ),
            ]

            result = parser.fetch_feeds(
                [
                    "https://test.com/feed1",
                    "https://test.com/feed2",
                ]
            )
            uow.commit()

        assert result["total_fetched"] == 1
        assert result["total_new"] == 1
        assert len(result["errors"]) == 1
        assert "HTTP 404" in result["errors"][0]["error"]
