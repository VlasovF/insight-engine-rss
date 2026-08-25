"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .api import (
    embedding_router,
    events_router,
    feeds_router,
    pipeline_router,
    vector_router,
)
from .database import engine
from .models import Base
from .utils import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add trace_id to each request."""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add trace_id to logger context.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or endpoint handler.

        Returns:
            HTTP response with X-Trace-Id header.

        """
        trace_id = request.headers.get("X-Trace-Id", str(uuid4()))
        request.state.trace_id = trace_id

        # Clear and bind trace_id to contextvars
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        response = await call_next(request)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        response.headers["X-Trace-Id"] = trace_id
        return response


# Create tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("application_startup", message="Starting Insight Engine API")
    yield
    logger.info("application_shutdown", message="Shutting down Insight Engine API")
    engine.dispose()


app = FastAPI(
    title="Insight Engine API",
    version="0.1.0",
    description="News analytics pipeline with dialectical insights",
    lifespan=lifespan,
)


app.add_middleware(TraceIdMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(feeds_router)
app.include_router(events_router)
app.include_router(vector_router)
app.include_router(embedding_router)
app.include_router(pipeline_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
