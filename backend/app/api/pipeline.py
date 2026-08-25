"""Pipeline management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..dependencies import get_uow
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


def get_embedding_service() -> OllamaClient:
    """Dependency injection for EmbeddingService."""
    return OllamaClient()


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

    Args:
        uow: Unit of Work instance.
        embedding_service: Embedding service instance.

    Returns:
        Statistics about processed events.

    """
    logger.info("embedding_pipeline_started")

    # Check Ollama availability
    if not embedding_service.health_check():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is not available",
        )

    # Check model availability
    if not embedding_service.check_model_availability():
        raise HTTPException(
            status_code=503,
            detail=f"Model '{embedding_service.embed_model}' not available in Ollama",
        )

    with uow.begin():
        # Get pending events
        pending_events = uow.events.get_pending(limit=settings.PIPELINE_MAX_EVENTS)

        if not pending_events:
            logger.info("embedding_pipeline_no_pending")
            return EmbeddingResponse(processed=0, duplicates_found=0, errors=0)

        logger.info(
            "embedding_pipeline_pending_count",
            count=len(pending_events),
        )

        # Get ChromaDB collection
        collection = get_chroma_client(
            collection_name=settings.CHROMA_COLLECTION,
        )

        processed = 0
        duplicates_found = 0
        errors = 0

        # Process each event
        for event in pending_events:
            try:
                # Prepare text for embedding (title + content)
                text = f"{event.title}\n{event.content}"
                text = text.strip()[:5000]  # Truncate to avoid token limits

                # Generate embedding
                embedding = embedding_service.get_embedding(text)

                if not embedding:
                    logger.warning(
                        "embedding_generation_failed",
                        event_id=event.id,
                        title=event.title[:50],
                    )
                    errors += 1
                    continue

                # Check for duplicates in ChromaDB
                results = collection.query(
                    query_embeddings=[embedding],  # type: ignore[arg-type]
                    n_results=1,
                    include=["distances"],
                )

                # Check if similar document exists
                is_duplicate = False
                if results["distances"] and results["distances"][0]:
                    distance = results["distances"][0][0]
                    # Convert cosine distance to similarity (1 - distance)
                    similarity = 1 - distance
                    if similarity >= settings.DUPLICATE_THRESHOLD:
                        is_duplicate = True
                        duplicates_found += 1
                        logger.info(
                            "duplicate_detected",
                            event_id=event.id,
                            similarity=similarity,
                            threshold=settings.DUPLICATE_THRESHOLD,
                        )

                # Store embedding in ChromaDB
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

                # Update event status
                if is_duplicate:
                    uow.events.mark_duplicate(event.id)
                else:
                    uow.events.update_status(event.id, "embedded")

                processed += 1

                logger.debug(
                    "event_embedded",
                    event_id=event.id,
                    title=event.title[:50],
                    is_duplicate=is_duplicate,
                )

            except Exception as e:
                logger.error(
                    "embedding_pipeline_event_failed",
                    event_id=event.id,
                    error=str(e),
                )
                errors += 1

        # Mark checkpoint
        uow.checkpoints.mark_completed("embedding_completed")

        logger.info(
            "embedding_pipeline_completed",
            processed=processed,
            duplicates_found=duplicates_found,
            errors=errors,
        )

        return EmbeddingResponse(
            processed=processed,
            duplicates_found=duplicates_found,
            errors=errors,
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
