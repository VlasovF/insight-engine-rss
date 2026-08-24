"""Vector database endpoints for testing."""

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..utils import get_logger
from ..vector import get_chroma_client, reset_collection

router = APIRouter(prefix="/api/vector", tags=["vector"])
logger = get_logger(__name__)


class VectorAddRequest(BaseModel):
    """Request model for adding vectors."""

    ids: list[str]
    embeddings: list[list[float]]
    metadatas: Optional[list[dict[str, Any]]] = None
    documents: Optional[list[str]] = None


class VectorAddResponse(BaseModel):
    """Response model for add vectors."""

    added_count: int


class VectorQueryRequest(BaseModel):
    """Request model for querying vectors."""

    query_embeddings: list[list[float]]
    n_results: int = 10


class VectorQueryResponse(BaseModel):
    """Response model for query vectors."""

    ids: list[list[str]]
    distances: list[list[float]]
    metadatas: Optional[list[list[dict[str, Any]]]] = None
    documents: Optional[list[list[str]]] = None


class VectorCountResponse(BaseModel):
    """Response model for count vectors."""

    count: int


@router.post("/add", response_model=VectorAddResponse)
async def add_vectors(request: VectorAddRequest) -> VectorAddResponse:
    """
    Add vectors to the collection.

    Args:
        request: Vector data to add.

    Returns:
        Number of vectors added.

    """
    collection = get_chroma_client()

    collection.add(
        ids=request.ids,
        embeddings=request.embeddings,  # type: ignore[arg-type]
        metadatas=request.metadatas,  # type: ignore[arg-type]
        documents=request.documents,
    )

    logger.info(
        "vectors_added",
        count=len(request.ids),
        collection="events",
    )

    return VectorAddResponse(added_count=len(request.ids))


@router.post("/query", response_model=VectorQueryResponse)
async def query_vectors(request: VectorQueryRequest) -> VectorQueryResponse:
    """
    Query vectors from the collection.

    Args:
        request: Query embeddings.

    Returns:
        Nearest neighbors.

    """
    collection = get_chroma_client()

    results = collection.query(
        query_embeddings=request.query_embeddings,  # type: ignore[arg-type]
        n_results=request.n_results,
        include=["distances", "metadatas", "documents"],
    )

    logger.info(
        "vectors_queried",
        n_results=request.n_results,
        collection="events",
    )

    return VectorQueryResponse(
        ids=results["ids"],
        distances=results.get("distances", []),  # type: ignore[arg-type]
        metadatas=results.get("metadatas"),  # type: ignore[arg-type]
        documents=results.get("documents"),
    )


@router.get("/count", response_model=VectorCountResponse)
async def count_vectors() -> VectorCountResponse:
    """
    Get total number of vectors in the collection.

    Returns:
        Total vector count.

    """
    collection = get_chroma_client()
    count = collection.count()
    logger.info("vectors_count", count=count, collection="events")
    return VectorCountResponse(count=count)


@router.delete("/reset", response_model=VectorCountResponse)
async def reset_vectors() -> VectorCountResponse:
    """
    Delete all vectors from the collection.

    Returns:
        Number of vectors deleted.

    """
    count = reset_collection()
    return VectorCountResponse(count=count)
