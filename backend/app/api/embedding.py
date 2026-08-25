"""Embedding endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services import OllamaClient
from ..utils import get_logger

router = APIRouter(prefix="/api/embedding", tags=["embedding"])
logger = get_logger(__name__)


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""

    texts: List[str] = Field(..., min_length=1, max_length=100)
    model: Optional[str] = Field(None, description="Override default model")


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""

    embeddings: List[List[float]]
    dimension: int
    model: str
    processed_count: int


class EmbeddingDimensionResponse(BaseModel):
    """Response for dimension check."""

    model: str
    dimension: int


class ModelCheckResponse(BaseModel):
    """Response for model availability check."""

    model: str
    available: bool
    message: Optional[str] = None


def get_embedding_service(
    model: Optional[str] = None,
) -> OllamaClient:
    """Dependency injection for EmbeddingService."""
    return OllamaClient(embed_model=model or "mxbai-embed-large:335m")


@router.post("/embed", response_model=EmbeddingResponse)
async def embed_texts(
    request: EmbeddingRequest,
    service: OllamaClient = Depends(get_embedding_service),
) -> EmbeddingResponse:
    """
    Generate embeddings for a list of texts.

    Args:
        request: Texts to embed.
        service: Embedding service instance.

    Returns:
        Embeddings for each text.

    """
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts cannot be empty")

    if len(request.texts) > 100:
        raise HTTPException(status_code=400, detail="maximum 100 texts per request")

    # Use custom model if provided
    if request.model:
        service.embed_model = request.model

    # Check model availability
    if not service.check_model_availability():
        raise HTTPException(
            status_code=503,
            detail=f"Model '{service.embed_model}' not available in Ollama",
        )

    embeddings = service.get_embeddings_batch(request.texts)
    dimension = service.get_embedding_dimension()

    # Count successful embeddings
    processed = sum(1 for e in embeddings if e)

    return EmbeddingResponse(
        embeddings=embeddings,
        dimension=dimension,
        model=service.embed_model,
        processed_count=processed,
    )


@router.get("/dimension", response_model=EmbeddingDimensionResponse)
async def get_embedding_dimension(
    model: Optional[str] = None,
    service: OllamaClient = Depends(get_embedding_service),
) -> EmbeddingDimensionResponse:
    """
    Get the embedding dimension for the current model.

    Args:
        model: Optional model name override.
        service: Embedding service instance.

    Returns:
        Model name and embedding dimension.

    """
    if model:
        service.embed_model = model

    dimension = service.get_embedding_dimension()
    return EmbeddingDimensionResponse(
        model=service.embed_model,
        dimension=dimension,
    )


@router.get("/check-model", response_model=ModelCheckResponse)
async def check_model_availability(
    model: Optional[str] = None,
    service: OllamaClient = Depends(get_embedding_service),
) -> ModelCheckResponse:
    """
    Check if the embedding model is available in Ollama.

    Args:
        model: Optional model name override.
        service: Embedding service instance.

    Returns:
        Model availability status.

    """
    if model:
        service.embed_model = model

    available = service.check_model_availability()
    return ModelCheckResponse(
        model=service.embed_model,
        available=available,
        message="Model is available" if available else "Model not found in Ollama",
    )
