"""RSS feed endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import get_uow
from ..services import RSSParserService
from ..uow import UnitOfWork

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


class FeedFetchRequest(BaseModel):
    """Request model for fetching feeds."""

    feed_urls: List[str]


class FeedFetchResponse(BaseModel):
    """Response model for feed fetch."""

    count: int
    new_count: int
    errors: List[dict]


@router.post("/fetch", response_model=FeedFetchResponse)
async def fetch_feeds(
    request: FeedFetchRequest,
    uow: UnitOfWork = Depends(get_uow),
) -> FeedFetchResponse:
    """
    Fetch and parse RSS feeds.

    Args:
        request: List of feed URLs to fetch.
        uow: Unit of Work instance.

    Returns:
        Statistics about fetched items.

    """
    if not request.feed_urls:
        raise HTTPException(status_code=400, detail="feed_urls cannot be empty")

    with uow.begin():
        parser = RSSParserService(uow.events)
        result = parser.fetch_feeds(request.feed_urls)

    return FeedFetchResponse(
        count=result["total_fetched"],
        new_count=result["total_new"],
        errors=result["errors"],
    )
