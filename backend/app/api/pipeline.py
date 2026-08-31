"""Pipeline management endpoints."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..dependencies import get_uow
from ..evaluation import (
    ConflictScoring,
    EvaluationPipeline,
    SurpriseScoring,
    UrgencyScoring,
)
from ..models import CheckpointStage, EventStatus
from ..services import OllamaClient
from ..uow import UnitOfWork
from ..utils import get_logger
from ..vector import get_chroma_client

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])
logger = get_logger(__name__)


class EmbeddingResponse(BaseModel):
    """Response model for embedding pipeline run."""

    processed: int
    duplicates_found: int
    errors: int
    batch_id: Optional[str] = None


class EvaluationResponse(BaseModel):
    """Response model for evaluation pipeline run."""

    processed: int
    errors: int
    batch_id: Optional[str] = None


class ResetResponse(BaseModel):
    """Response model for reset pipeline."""

    reset_count: int


class PipelineProgressResponse(BaseModel):
    """Response model for pipeline progress."""

    completed_stages: List[str]
    progress: dict
    percentage: int
    last_completed: Optional[str]


class CheckpointsSummaryResponse(BaseModel):
    """Response model for checkpoints summary."""

    checkpoints: List[dict]


def get_embedding_service() -> OllamaClient:
    """Dependency injection for EmbeddingService."""
    return OllamaClient()


def get_evaluation_pipeline() -> EvaluationPipeline:
    """Dependency injection for EvaluationPipeline."""
    ollama_client = OllamaClient()
    pipeline = EvaluationPipeline()
    pipeline.add_strategy(UrgencyScoring(ollama_client))
    pipeline.add_strategy(ConflictScoring(ollama_client))
    pipeline.add_strategy(SurpriseScoring(ollama_client))
    return pipeline


def _check_ollama_availability(embedding_service: OllamaClient) -> None:
    """Check Ollama and model availability."""
    if not embedding_service.health_check():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is not available",
        )

    if not embedding_service.check_model_availability():
        raise HTTPException(
            status_code=503,
            detail=f"Model '{embedding_service.embed_model}' not available in Ollama",
        )


def _process_single_event(
    event,
    collection,
    embedding_service: OllamaClient,
) -> Tuple[bool, bool, Optional[Exception]]:
    """
    Process a single event: embed, check duplicates, store.

    Returns:
        Tuple of (is_processed, is_duplicate, error)

    """
    try:
        # Prepare text for embedding
        text = f"{event.title}\n{event.content}"
        text = text.strip()[:5000]

        # Generate embedding
        embedding = embedding_service.get_embedding(text)

        if not embedding:
            logger.warning(
                "embedding_generation_failed",
                event_id=event.id,
                title=event.title[:50],
            )
            return False, False, None

        # Check for duplicates
        results = collection.query(
            query_embeddings=[embedding],  # type: ignore[arg-type]
            n_results=1,
            include=["distances"],
        )

        is_duplicate = False
        if results["distances"] and results["distances"][0]:
            distance = results["distances"][0][0]
            similarity = 1 - distance
            if similarity >= settings.DUPLICATE_THRESHOLD:
                is_duplicate = True
                logger.info(
                    "duplicate_detected",
                    event_id=event.id,
                    similarity=similarity,
                    threshold=settings.DUPLICATE_THRESHOLD,
                )

        # Store embedding
        collection.add(
            ids=[event.id],
            embeddings=[embedding],  # type: ignore[arg-type]
            metadatas=[
                {
                    "title": event.title[:200],
                    "status": event.status,
                }
            ],
            documents=[text[:1000]],
        )

        return True, is_duplicate, None

    except Exception as e:
        logger.error(
            "embedding_pipeline_event_failed",
            event_id=event.id,
            error=str(e),
        )
        return False, False, e


def _update_event_status(
    uow: UnitOfWork,
    event_id: str,
    is_duplicate: bool,
) -> None:
    """Update event status after embedding."""
    if is_duplicate:
        uow.events.mark_duplicate(event_id)
    else:
        uow.events.update_status(event_id, EventStatus.EMBEDDED)


@router.post("/run_embedding", response_model=EmbeddingResponse)
async def run_embedding_pipeline(
    uow: UnitOfWork = Depends(get_uow),
    embedding_service: OllamaClient = Depends(get_embedding_service),
) -> EmbeddingResponse:
    """
    Run embedding pipeline for all pending events.

    Process:
    1. Get all pending events
    2. Generate embeddings for each
    3. Check for duplicates in ChromaDB
    4. Update event status and mark duplicates
    5. Save checkpoint

    Args:
        uow: Unit of Work instance.
        embedding_service: Embedding service instance.

    Returns:
        Statistics about processed events.

    """
    logger.info("embedding_pipeline_started")

    _check_ollama_availability(embedding_service)

    with uow.begin():
        # Get all pending events
        pending_events = uow.events.get_pending(limit=settings.PIPELINE_MAX_EVENTS)

        if not pending_events:
            logger.info("embedding_pipeline_no_pending")
            return EmbeddingResponse(
                processed=0, duplicates_found=0, errors=0, batch_id=""
            )

        # Get already processed event IDs (from all embedding checkpoints)
        processed_ids = set(
            uow.checkpoints.get_processed_event_ids(CheckpointStage.EMBEDDING_COMPLETED)
        )

        # Filter out already processed events
        events_to_process = [e for e in pending_events if e.id not in processed_ids]

        if not events_to_process:
            logger.info("embedding_pipeline_no_new_events")
            return EmbeddingResponse(
                processed=0, duplicates_found=0, errors=0, batch_id=""
            )

        logger.info(
            "embedding_pipeline_events_to_process",
            total_pending=len(pending_events),
            already_processed=len(processed_ids),
            new_events=len(events_to_process),
        )

        # Get ChromaDB collection
        collection = get_chroma_client(
            collection_name=settings.CHROMA_COLLECTION,
        )

        processed = 0
        duplicates_found = 0
        errors = 0
        processed_event_ids = []

        for event in events_to_process:
            is_processed, is_duplicate, error = _process_single_event(
                event,
                collection,
                embedding_service,
            )

            if error:
                errors += 1
                continue

            if is_processed:
                _update_event_status(uow, event.id, is_duplicate)
                processed += 1
                processed_event_ids.append(event.id)
                if is_duplicate:
                    duplicates_found += 1

        # Create checkpoint for this batch
        if processed_event_ids:
            metadata = {
                "processed": processed,
                "duplicates_found": duplicates_found,
                "errors": errors,
                "total_pending": len(pending_events),
                "new_events": len(events_to_process),
            }
            checkpoint = uow.checkpoints.create_checkpoint(
                stage_name=CheckpointStage.EMBEDDING_COMPLETED,
                event_ids=processed_event_ids,
                metadata=metadata,
            )
            batch_id = checkpoint.batch_id
        else:
            batch_id = ""

        logger.info(
            "embedding_pipeline_completed",
            processed=processed,
            duplicates_found=duplicates_found,
            errors=errors,
            batch_id=batch_id,
        )

        return EmbeddingResponse(
            processed=processed,
            duplicates_found=duplicates_found,
            errors=errors,
            batch_id=batch_id,
        )


@router.post("/run_evaluation", response_model=EvaluationResponse)
async def run_evaluation_pipeline(
    uow: UnitOfWork = Depends(get_uow),
    pipeline: EvaluationPipeline = Depends(get_evaluation_pipeline),
) -> EvaluationResponse:
    """
    Run evaluation pipeline for all embedded non-duplicate events.

    Process:
    1. Get all embedded non-duplicate events
    2. Evaluate each using three scoring strategies
    3. Store evaluation results in event.evaluation_data
    4. Update event status to evaluated
    5. Save checkpoint

    Args:
        uow: Unit of Work instance.
        pipeline: Evaluation pipeline instance.

    Returns:
        Statistics about processed events.

    """
    logger.info("evaluation_pipeline_started")

    with uow.begin():
        # Get all embedded non-duplicate events
        events = uow.events.get_non_duplicates(
            status=EventStatus.EMBEDDED,
            limit=settings.PIPELINE_MAX_EVENTS,
        )

        if not events:
            logger.info("evaluation_pipeline_no_events")
            return EvaluationResponse(processed=0, errors=0, batch_id="")

        # Get already processed event IDs (from all evaluation checkpoints)
        processed_ids = set(
            uow.checkpoints.get_processed_event_ids(
                CheckpointStage.EVALUATION_COMPLETED
            )
        )

        # Filter out already processed events
        events_to_process = [e for e in events if e.id not in processed_ids]

        if not events_to_process:
            logger.info("evaluation_pipeline_no_new_events")
            return EvaluationResponse(processed=0, errors=0, batch_id="")

        logger.info(
            "evaluation_pipeline_events_to_process",
            total_available=len(events),
            already_processed=len(processed_ids),
            new_events=len(events_to_process),
        )

        processed = 0
        errors = 0
        processed_event_ids = []

        for event in events_to_process:
            try:
                result = pipeline.evaluate_event(event)
                event.evaluation_data = result
                event.status = EventStatus.EVALUATED
                processed += 1
                processed_event_ids.append(event.id)
            except Exception as e:
                logger.error(
                    "evaluation_pipeline_event_failed",
                    event_id=event.id,
                    error=str(e),
                )
                errors += 1

        # Create checkpoint for this batch
        if processed_event_ids:
            metadata = {
                "processed": processed,
                "errors": errors,
                "total_available": len(events),
                "new_events": len(events_to_process),
            }
            checkpoint = uow.checkpoints.create_checkpoint(
                stage_name=CheckpointStage.EVALUATION_COMPLETED,
                event_ids=processed_event_ids,
                metadata=metadata,
            )
            batch_id = checkpoint.batch_id
        else:
            batch_id = ""

        logger.info(
            "evaluation_pipeline_completed",
            processed=processed,
            errors=errors,
            batch_id=batch_id,
        )

        return EvaluationResponse(
            processed=processed,
            errors=errors,
            batch_id=batch_id,
        )


@router.get("/status", response_model=dict)
async def get_pipeline_status(
    uow: UnitOfWork = Depends(get_uow),
) -> dict:
    """
    Get current pipeline status with event counts by stage.

    Args:
        uow: Unit of Work instance.

    Returns:
        Dictionary with counts per status.

    """
    with uow.begin():
        counts = uow.events.count_by_status()

    return counts


@router.get("/progress", response_model=PipelineProgressResponse)
async def get_pipeline_progress(
    uow: UnitOfWork = Depends(get_uow),
) -> PipelineProgressResponse:
    """
    Get overall pipeline progress with checkpoint information.

    Args:
        uow: Unit of Work instance.

    Returns:
        Pipeline progress information.

    """
    with uow.begin():
        progress = uow.checkpoints.get_pipeline_progress()

    return PipelineProgressResponse(
        completed_stages=progress["completed_stages"],
        progress=progress["progress"],
        percentage=progress["percentage"],
        last_completed=progress["last_completed"],
    )


@router.get("/checkpoints", response_model=CheckpointsSummaryResponse)
async def get_checkpoints_summary(
    uow: UnitOfWork = Depends(get_uow),
) -> CheckpointsSummaryResponse:
    """Get summary of all checkpoints."""
    with uow.begin():
        checkpoints = uow.checkpoints.get_checkpoints_summary()

    return CheckpointsSummaryResponse(checkpoints=checkpoints)


@router.post("/reset_from_stage", response_model=ResetResponse)
async def reset_pipeline_from_stage(
    stage: str,
    uow: UnitOfWork = Depends(get_uow),
) -> ResetResponse:
    """
    Reset events to a specific pipeline stage.

    Args:
        stage: Target stage ("embedding" or "evaluation").
        uow: Unit of Work instance.

    Returns:
        Number of events reset.

    """
    valid_stages = ["embedding", "evaluation"]
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {valid_stages}",
        )

    logger.warning("pipeline_reset_requested", stage=stage)

    with uow.begin():
        # Reset events
        reset_count = uow.events.reset_from_stage(stage)

        # Delete corresponding checkpoint
        checkpoint_name = f"{stage}_completed"
        try:
            uow.checkpoints.delete_by_stage(checkpoint_name)
        except ValueError:
            pass

        # Also delete any downstream checkpoints
        if stage == "embedding":
            try:
                uow.checkpoints.delete_by_stage(CheckpointStage.EVALUATION_COMPLETED)
            except ValueError:
                pass
            try:
                uow.checkpoints.delete_by_stage(CheckpointStage.INSIGHT_GENERATED)
            except ValueError:
                pass

        logger.info(
            "pipeline_reset_completed",
            stage=stage,
            reset_count=reset_count,
        )

    return ResetResponse(reset_count=reset_count)
