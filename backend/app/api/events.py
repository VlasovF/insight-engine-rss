"""Event endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from ..dependencies import get_uow
from ..uow import UnitOfWork

router = APIRouter(prefix="/api/events", tags=["events"])


class EventResponse(BaseModel):
    """Response model for event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    source_url: Optional[str]
    published_at: Optional[datetime]
    status: str
    is_duplicate: bool
    content_hash: str
    evaluation_data: Optional[dict]
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    """Response model for event list."""

    items: List[EventResponse]
    total: int


class DeleteEventsResponse(BaseModel):
    """Response model for delete events."""

    deleted_count: int


@router.get("/", response_model=EventListResponse)
async def get_events(
    status: Optional[str] = Query(
        None, description="Filter by status: pending, embedded, evaluated"
    ),
    is_duplicate: Optional[bool] = Query(
        None, description="Filter by duplicate status"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    uow: UnitOfWork = Depends(get_uow),
) -> EventListResponse:
    """
    Get events with optional filters.

    Args:
        status: Filter by event status.
        is_duplicate: Filter by duplicate flag.
        limit: Maximum number of items.
        offset: Number of items to skip.
        uow: Unit of Work instance.

    Returns:
        List of events matching filters.

    """
    with uow.begin():
        # Build query
        query = uow.events._session.query(uow.events._model_class)

        if status:
            query = query.filter(uow.events._model_class.status == status)

        if is_duplicate is not None:
            query = query.filter(uow.events._model_class.is_duplicate == is_duplicate)

        total = query.count()
        items = query.offset(offset).limit(limit).all()

        event_list = EventListResponse(
            items=[EventResponse.model_validate(item) for item in items],
            total=total,
        )

    return event_list


@router.delete("/", response_model=DeleteEventsResponse)
async def delete_all_events(
    uow: UnitOfWork = Depends(get_uow),
) -> DeleteEventsResponse:
    """
    Delete all events. Use with caution.

    Args:
        uow: Unit of Work instance.

    Returns:
        Number of deleted events.

    """
    with uow.begin():
        events = uow.events.get_all(limit=10000)
        count = len(events)

        for event in events:
            uow.events.delete(event)

    return DeleteEventsResponse(deleted_count=count)
