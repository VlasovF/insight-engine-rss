"""API routers."""

from .embedding import router as embedding_router
from .events import router as events_router
from .feeds import router as feeds_router
from .vector import router as vector_router

__all__ = ["feeds_router", "events_router", "vector_router", "embedding_router"]
