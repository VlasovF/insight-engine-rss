"""Insight generation endpoints with SSE streaming."""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from structlog import get_logger

from ..config import settings
from ..dependencies import get_uow
from ..models import CheckpointStage, EventStatus, Insight
from ..services import InsightGenerator
from ..uow import UnitOfWork

router = APIRouter(prefix="/api/insights", tags=["insights"])
logger = get_logger(__name__)


class InsightResponse(BaseModel):
    """Response model for insight."""

    id: str
    content: str
    event_ids: Optional[List[str]]
    event_count: int
    stages: Optional[dict]
    created_at: str


class InsightsListResponse(BaseModel):
    """Response model for insights list."""

    items: List[InsightResponse]
    total: int


def get_insight_generator() -> InsightGenerator:
    """Dependency injection for InsightGenerator."""
    return InsightGenerator()


def _extract_event_data(event) -> Dict[str, Any]:
    """
    Extract event data and scores without accessing
    lazy-loaded attributes.

    Args:
        event: Event object (may be detached).

    Returns:
        Dictionary with event data and scores.

    """  # noqa D205
    # Access only attributes that are already loaded
    # Use getattr with defaults for safety
    return {
        "id": getattr(event, "id", ""),
        "title": getattr(event, "title", ""),
        "content": getattr(event, "content", ""),
        "source_url": getattr(event, "source_url", None),
        "published_at": getattr(event, "published_at", None),
        "status": getattr(event, "status", ""),
        "is_duplicate": getattr(event, "is_duplicate", False),
        "content_hash": getattr(event, "content_hash", ""),
        # Use evaluation_data directly if available, with safe access
        "evaluation_data": getattr(event, "evaluation_data", None),
        "created_at": getattr(event, "created_at", None),
        "updated_at": getattr(event, "updated_at", None),
    }


def _get_event_scores_from_data(event_data: Dict[str, Any]) -> Dict[str, float]:
    """Extract scores from event data dictionary."""
    scores = {"urgency": 0.0, "conflict": 0.0, "surprise": 0.0}

    evaluation_data = event_data.get("evaluation_data")
    if evaluation_data and isinstance(evaluation_data, dict):
        results = evaluation_data.get("results", {})
        for key in scores.keys():
            if key in results and isinstance(results[key], dict):
                scores[key] = results[key].get("score", 0.0)

    return scores


async def _stream_insight_generation(
    event_data_list: List[Dict[str, Any]],
    generator: InsightGenerator,
    uow: UnitOfWork,
) -> AsyncGenerator[str, None]:
    """
    Stream insight generation stages via SSE.

    Args:
        event_data_list: List of event data dictionaries.
        generator: InsightGenerator instance.
        uow: Unit of Work for saving results.

    Yields:
        SSE formatted messages for each stage.

    """
    if not event_data_list:
        yield f"data: {
            json.dumps(
                {'stage': 'error', 'error': 'No event data provided', 'status': 'error'}
            )
        }\n\n"
        return

    # Stage 1: Analyst
    yield f"data: {
        json.dumps(
            {'stage': 'analyst', 'content': 'Starting analysis...', 'status': 'start'}
        )
    }\n\n"

    try:
        analyst_prompt = generator._get_analyst_prompt(event_data_list)
        analyst_response = generator.ollama_client.generate_text(
            analyst_prompt,
            temperature=0.5,
            max_tokens=2000,
        )

        yield f"data: {
            json.dumps(
                {'stage': 'analyst', 'content': analyst_response, 'status': 'complete'}
            )
        }\n\n"
    except Exception as e:
        logger.error("analyst_stage_failed", error=str(e))
        yield f"data: {
            json.dumps({'stage': 'analyst', 'error': str(e), 'status': 'error'})
        }\n\n"
        return

    # Stage 2: Skeptic
    yield f"data: {
        json.dumps(
            {'stage': 'skeptic', 'content': 'Starting critique...', 'status': 'start'}
        )
    }\n\n"

    try:
        skeptic_prompt = generator._get_skeptic_prompt(analyst_response)
        skeptic_response = generator.ollama_client.generate_text(
            skeptic_prompt,
            temperature=0.5,
            max_tokens=1500,
        )

        yield f"data: {
            json.dumps(
                {'stage': 'skeptic', 'content': skeptic_response, 'status': 'complete'}
            )
        }\n\n"
    except Exception as e:
        logger.error("skeptic_stage_failed", error=str(e))
        yield f"data: {
            json.dumps({'stage': 'skeptic', 'error': str(e), 'status': 'error'})
        }\n\n"
        return

    # Stage 3: Synthesis
    yield f"data: {
        json.dumps(
            {
                'stage': 'synthesis',
                'content': 'Generating synthesis...',
                'status': 'start',
            }
        )
    }\n\n"

    try:
        synthesis_prompt = generator._get_synthesis_prompt(
            analyst_response,
            skeptic_response,
        )
        synthesis_response = generator.ollama_client.generate_text(
            synthesis_prompt,
            temperature=0.3,
            max_tokens=1500,
        )

        yield f"data: {
            json.dumps(
                {
                    'stage': 'synthesis',
                    'content': synthesis_response,
                    'status': 'complete',
                }
            )
        }\n\n"
    except Exception as e:
        logger.error("synthesis_stage_failed", error=str(e))
        yield f"data: {
            json.dumps({'stage': 'synthesis', 'error': str(e), 'status': 'error'})
        }\n\n"
        return

    # Save insight to database
    try:
        event_ids = [ed["id"] for ed in event_data_list if ed.get("id")]
        stages = {
            "analyst": analyst_response,
            "skeptic": skeptic_response,
            "synthesis": synthesis_response,
        }

        insight = Insight(
            content=synthesis_response,
            event_ids=event_ids,
            event_count=len(event_ids),
            stages=stages,
        )

        with uow.begin():
            uow.insights.add(insight)
            uow.checkpoints.create_checkpoint(
                stage_name=CheckpointStage.INSIGHT_GENERATED,
                event_ids=event_ids,
                metadata={
                    "insight_id": insight.id,
                    "event_count": len(event_ids),
                },
            )

        yield f"data: {
            json.dumps(
                {
                    'stage': 'done',
                    'insight_id': insight.id,
                    'content': synthesis_response,
                    'status': 'complete',
                }
            )
        }\n\n"

    except Exception as e:
        logger.error("insight_save_failed", error=str(e))
        yield f"data: {
            json.dumps({'stage': 'done', 'error': str(e), 'status': 'error'})
        }\n\n"


@router.get("/stream")
async def stream_insight(
    uow: UnitOfWork = Depends(get_uow),
    generator: InsightGenerator = Depends(get_insight_generator),
) -> StreamingResponse:
    """
    Stream insight generation via Server-Sent Events (SSE).

    Returns:
        SSE stream with analyst, skeptic, and synthesis stages.

    """
    logger.info("insight_stream_requested")

    # Collect all event data while session is active
    with uow.begin():
        # Get evaluated non-duplicate events
        events = uow.events.get_non_duplicates(
            status=EventStatus.EVALUATED,
            limit=100,
        )

        if not events:
            raise HTTPException(
                status_code=404,
                detail="No evaluated events found. Run evaluation first.",
            )

        # Extract all data from events while session is active
        event_data_list = []
        for event in events:
            event_data = _extract_event_data(event)
            scores = _get_event_scores_from_data(event_data)

            # Add scores to event data
            event_data["urgency"] = scores["urgency"]
            event_data["conflict"] = scores["conflict"]
            event_data["surprise"] = scores["surprise"]

            # Calculate composite score
            event_data["composite"] = (
                scores["conflict"] + scores["urgency"] + (scores["surprise"] * 0.5)
            )

            event_data_list.append(event_data)

        if not event_data_list:
            raise HTTPException(
                status_code=404,
                detail="No evaluable events found.",
            )

        # Sort by composite score descending and select top K
        event_data_list.sort(key=lambda x: x.get("composite", 0), reverse=True)
        top_events = event_data_list[: settings.INSIGHT_TOP_K]

        if len(top_events) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 2 events for insight, got {len(top_events)}",
            )

        logger.info(
            "insight_stream_events_selected",
            count=len(top_events),
            top_scores=[f"{e.get('composite', 0):.2f}" for e in top_events],
        )

    # Generate insight using the extracted data (no session dependency)
    return StreamingResponse(
        _stream_insight_generation(top_events, generator, uow),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/", response_model=InsightsListResponse)
async def get_insights(
    limit: int = 10,
    offset: int = 0,
    uow: UnitOfWork = Depends(get_uow),
) -> InsightsListResponse:
    """
    Get list of generated insights.

    Args:
        limit: Maximum number of insights.
        offset: Number of insights to skip.
        uow: Unit of Work instance.

    Returns:
        List of insights.

    """
    with uow.begin():
        insights = uow.insights.get_latest(limit=limit + offset)

    items = insights[offset : offset + limit]

    return InsightsListResponse(
        items=[
            InsightResponse(
                id=i.id,
                content=i.content,
                event_ids=i.event_ids,
                event_count=i.event_count,
                stages=i.stages,
                created_at=i.created_at.isoformat(),
            )
            for i in items
        ],
        total=len(insights),
    )


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> InsightResponse:
    """
    Get a specific insight by ID.

    Args:
        insight_id: Insight ID.
        uow: Unit of Work instance.

    Returns:
        Insight data.

    """
    with uow.begin():
        insight = uow.insights.get_by_id(insight_id)

    if not insight:
        raise HTTPException(status_code=404, detail=f"Insight {insight_id} not found")

    return InsightResponse(
        id=insight.id,
        content=insight.content,
        event_ids=insight.event_ids,
        event_count=insight.event_count,
        stages=insight.stages,
        created_at=insight.created_at.isoformat(),
    )


@router.delete("/{insight_id}")
async def delete_insight(
    insight_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """
    Delete an insight by ID.

    Args:
        insight_id: Insight ID.
        uow: Unit of Work instance.

    Returns:
        Deletion status.

    """
    with uow.begin():
        insight = uow.insights.get_by_id(insight_id)

        if not insight:
            raise HTTPException(
                status_code=404, detail=f"Insight {insight_id} not found"
            )

        uow.insights.delete(insight)

    return {"status": "deleted", "id": insight_id}
