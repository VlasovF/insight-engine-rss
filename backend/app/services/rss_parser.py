"""RSS parser service for fetching and parsing feeds."""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser
import httpx
from structlog import get_logger

from ..models import Event
from ..repositories import EventRepository

logger = get_logger(__name__)


class RSSParserService:
    """Service for parsing RSS feeds and creating Event entities."""

    def __init__(self, event_repository: EventRepository):
        """Initialize RSS parser service."""
        self._event_repo = event_repository
        self._timeout = 30.0

    def fetch_feeds(self, feed_urls: List[str]) -> Dict[str, Any]:
        """
        Fetch and parse multiple RSS feeds.

        Args:
            feed_urls: List of RSS feed URLs.

        Returns:
            Dictionary with statistics about fetched items.

        """
        total_fetched = 0
        total_new = 0
        errors = []

        for url in feed_urls:
            try:
                result = self._fetch_single_feed(url)
                total_fetched += result["fetched"]
                total_new += result["new"]
                if result.get("error"):
                    errors.append({"url": url, "error": result["error"]})
            except Exception as e:
                logger.error("feed_fetch_error", url=url, error=str(e))
                errors.append({"url": url, "error": str(e)})

        return {
            "total_fetched": total_fetched,
            "total_new": total_new,
            "errors": errors,
        }

    def _fetch_single_feed(self, url: str) -> Dict[str, Any]:
        """Fetch and parse a single RSS feed."""
        try:
            # Fetch feed with timeout
            response = httpx.get(url, timeout=self._timeout)
            response.raise_for_status()

            # Parse feed
            feed = feedparser.parse(response.text)

            if feed.bozo:
                logger.warning("feed_parse_warning", url=url, error=feed.bozo_exception)

            items = feed.entries
            new_count = 0

            for entry in items:
                if self._save_entry(entry, url):
                    new_count += 1

            return {
                "fetched": len(items),
                "new": new_count,
                "error": None,
            }

        except httpx.TimeoutException:
            logger.error("feed_timeout", url=url)
            return {"fetched": 0, "new": 0, "error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            logger.error("feed_http_error", url=url, status=e.response.status_code)
            return {"fetched": 0, "new": 0, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error("feed_unknown_error", url=url, error=str(e))
            return {"fetched": 0, "new": 0, "error": str(e)}

    def _save_entry(self, entry: Dict[str, Any], source_url: str) -> bool:
        """
        Save a feed entry as an Event.

        Returns:
            True if new event was saved, False if duplicate.

        """
        title = entry.get("title", "Untitled")
        content = self._extract_content(entry)

        # Skip if no content
        if not content.strip():
            logger.debug("empty_content_skipped", title=title)
            return False

        # Generate content hash
        content_hash = hashlib.md5((title + content).encode("utf-8")).hexdigest()

        # Check for duplicate
        existing = self._event_repo.get_by_hash(content_hash)
        if existing:
            logger.debug("duplicate_skipped", title=title, hash=content_hash[:8])
            return False

        # Parse published date
        published_at = self._parse_published_date(entry)

        # Create event
        event = Event(
            title=title[:500],  # Truncate to avoid DB issues
            content=content[:5000],  # Truncate
            source_url=source_url,
            published_at=published_at,
            content_hash=content_hash,
            status="pending",
            is_duplicate=False,
        )

        self._event_repo.add(event)
        logger.info("event_created", id=event.id, title=title[:50])

        return True

    def _extract_content(self, entry: Dict[str, Any]) -> str:
        """Extract content from feed entry."""
        # Try different content fields
        content = (
            entry.get("content", [{}])[0].get("value", "")
            if entry.get("content")
            else ""
        )

        if not content:
            content = entry.get("summary", "")

        if not content:
            content = entry.get("description", "")

        if not content:
            content = entry.get("title", "")

        return content.strip()

    def _parse_published_date(self, entry: Dict[str, Any]) -> Optional[datetime]:
        """Parse published date from feed entry."""
        published_str = entry.get("published") or entry.get("updated")

        if published_str:
            try:
                # Try standard feedparser parsing
                from feedparser import _parse_date

                parsed = _parse_date(published_str)
                if parsed:
                    return parsed
            except Exception:
                pass

            # Try common formats
            formats = [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(published_str, fmt)
                except ValueError:
                    continue

        # Fallback to current time
        return datetime.now(timezone.utc)
