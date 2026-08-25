"""Service layer for business logic."""

from .embedding import EmbeddingError, OllamaClient, ServiceUnavailableError
from .rss_parser import RSSParserService

# Alias for backward compatibility
EmbeddingService = OllamaClient

__all__ = [
    "RSSParserService",
    "OllamaClient",
    "EmbeddingService",
    "EmbeddingError",
    "ServiceUnavailableError",
]
