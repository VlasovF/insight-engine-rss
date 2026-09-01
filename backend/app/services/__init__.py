"""Service layer for business logic."""

from .embedding import EmbeddingError, OllamaClient, ServiceUnavailableError
from .insight_generator import InsightGenerator
from .rss_parser import RSSParserService

# Alias for backward compatibility
EmbeddingService = OllamaClient

__all__ = [
    "RSSParserService",
    "OllamaClient",
    "EmbeddingService",
    "EmbeddingError",
    "ServiceUnavailableError",
    "InsightGenerator",
]
