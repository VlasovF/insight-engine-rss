"""API routers."""

from .embedding import router as embedding_router
from .events import router as events_router
from .feeds import router as feeds_router
from .insights import router as insights_router
from .pipeline import router as pipeline_router
from .vector import router as vector_router

__all__ = [
    "feeds_router",
    "events_router",
    "vector_router",
    "embedding_router",
    "pipeline_router",
    "insights_router",
]
