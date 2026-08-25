"""Ollama API client for embeddings and LLM."""

import json
import time
from typing import Any, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..utils import get_logger

logger = get_logger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class ServiceUnavailableError(Exception):
    """Raised when Ollama service is unavailable."""

    pass


class OllamaClient:
    """HTTP client for Ollama API."""

    def __init__(
        self,
        host: str = "ollama",
        port: int = 11434,
        embed_model: str = "mxbai-embed-large:335m",
        timeout: int = 60,
    ):
        """
        Initialize Ollama client.

        Args:
            host: Ollama API host.
            port: Ollama API port.
            embed_model: Embedding model name.
            timeout: Request timeout in seconds.

        """
        self.base_url = f"http://{host}:{port}"
        self.embed_model = embed_model
        self.timeout = timeout
        self._session: Optional[httpx.Client] = None
        self._dimension: Optional[int] = None

    @property
    def session(self) -> httpx.Client:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = httpx.Client(
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._session

    def _check_connection(self) -> None:
        """Check if Ollama is reachable."""
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]

            # Check if embed model exists
            if not any(self.embed_model in m for m in models):
                logger.warning(
                    "embedding_model_not_found",
                    model=self.embed_model,
                    available_models=models[:5],
                )

            logger.info("ollama_connected", host=self.base_url)
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(
                f"Connection failed to Ollama at {self.base_url}: {str(e)}"
            ) from e
        except Exception as e:
            raise ServiceUnavailableError(
                f"Unexpected error connecting to Ollama: {str(e)}"
            ) from e

    def health_check(self) -> bool:
        """
        Check if Ollama is healthy.

        Returns:
            True if healthy.

        """
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for a single text.

        Args:
            text: Input text.

        Returns:
            Embedding vector as list of floats.

        Raises:
            EmbeddingError: If embedding generation fails.

        """
        if not text or not text.strip():
            logger.warning("empty_text_for_embedding")
            return []

        try:
            resp = self.session.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text.strip()},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            embedding = data.get("embedding")

            if not embedding:
                raise EmbeddingError("Empty embedding returned from Ollama")

            # Store dimension if not set
            if self._dimension is None and embedding:
                self._dimension = len(embedding)
                logger.info(
                    "embedding_dimension_detected",
                    model=self.embed_model,
                    dimension=self._dimension,
                )

            return embedding  # type: ignore[no-any-return]
        except httpx.TimeoutException as e:
            logger.error("embedding_timeout", error=str(e))
            raise EmbeddingError(f"Timeout getting embedding: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            logger.error("embedding_http_error", status=e.response.status_code)
            raise EmbeddingError(f"HTTP error: {str(e)}") from e
        except json.JSONDecodeError as e:
            logger.error("embedding_invalid_json", error=str(e))
            raise EmbeddingError(f"Invalid JSON response: {str(e)}") from e

    def get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 10,
        delay: float = 0.1,
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of input texts.
            batch_size: Number of texts per batch
            (not used for Ollama, kept for API compatibility).
            delay: Delay between requests in seconds.

        Returns:
            List of embedding vectors. Empty list for failed texts.

        """
        embeddings = []
        for i, text in enumerate(texts):
            try:
                embedding = self.get_embedding(text)
                embeddings.append(embedding)
                logger.debug(
                    "embedding_batch_progress",
                    current=i + 1,
                    total=len(texts),
                )
            except EmbeddingError as e:
                logger.error(
                    "embedding_batch_failed",
                    text=text[:100],
                    error=str(e),
                )
                embeddings.append([])

            # Small delay between requests
            if len(texts) > 1 and i < len(texts) - 1:
                time.sleep(delay)

        return embeddings

    def get_embedding_dimension(self) -> int:
        """
        Get the embedding dimension for the current model.

        Returns:
            Dimension of embeddings.

        Raises:
            EmbeddingError: If unable to determine dimension.

        """
        if self._dimension is not None:
            return self._dimension

        # Try to get dimension by embedding a test text
        test_text = "test"
        embedding = self.get_embedding(test_text)
        if embedding:
            self._dimension = len(embedding)
            logger.info(
                "embedding_dimension_detected",
                model=self.embed_model,
                dimension=self._dimension,
            )
            return self._dimension

        raise EmbeddingError("Unable to determine embedding dimension")

    def check_model_availability(self) -> bool:
        """
        Check if the embedding model is available in Ollama.

        Returns:
            True if model is available, False otherwise.

        """
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if model exists (exact match or prefix match)
            for name in model_names:
                if name == self.embed_model or name.startswith(self.embed_model):
                    return True

            logger.warning(
                "model_not_found",
                model=self.embed_model,
                available_models=model_names[:10],
            )
            return False
        except Exception as e:
            logger.error("model_check_failed", error=str(e))
            return False

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None


# Alias for backward compatibility
EmbeddingService = OllamaClient
