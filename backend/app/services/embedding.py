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

from ..config import settings
from ..utils import get_logger

logger = get_logger(__name__)


class ObsidianAIError(Exception):
    """Base exception for all application errors."""

    pass


class ConfigurationError(ObsidianAIError):
    """Raised when configuration is invalid."""

    pass


class ServiceUnavailableError(Exception):
    """Raised when Ollama service is unavailable."""

    pass


class EmbeddingError(ObsidianAIError):
    """Raised when embedding generation fails."""

    pass


class QdrantError(ObsidianAIError):
    """Raised when Qdrant operations fail."""

    pass


class FileProcessingError(ObsidianAIError):
    """Raised when file processing fails."""

    pass


class DeduplicationError(ObsidianAIError):
    """Raised when duplicate detection fails."""

    pass


class LLMGenerationError(ObsidianAIError):
    """Raised when LLM text generation fails."""

    pass


class OllamaClient:
    """HTTP client for Ollama API."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        embed_model: Optional[str] = None,
        llm_model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize Ollama client.

        Args:
            host: Ollama API host. Defaults to settings.
            port: Ollama API port. Defaults to settings.
            embed_model: Embedding model name. Defaults to settings.
            llm_model: LLM model name. Defaults to settings.
            timeout: Request timeout in seconds. Defaults to settings.

        """
        self.host = host or settings.OLLAMA_HOST
        self.port = port or settings.OLLAMA_PORT
        self.embed_model = embed_model or settings.OLLAMA_EMBED_MODEL
        self.llm_model = llm_model or settings.OLLAMA_LLM_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        self.base_url = f"http://{self.host}:{self.port}"
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

            if self._dimension is None and embedding:
                self._dimension = len(embedding)
                logger.info(
                    "embedding_dimension_detected",
                    model=self.embed_model,
                    dimension=self._dimension,
                )

            return embedding
        except httpx.TimeoutException as e:
            logger.error("embedding_timeout", error=str(e))
            raise EmbeddingError(f"Timeout getting embedding: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            logger.error("embedding_http_error", status=e.response.status_code)
            raise EmbeddingError(f"HTTP error: {str(e)}") from e
        except json.JSONDecodeError as e:
            logger.error("embedding_invalid_json", error=str(e))
            raise EmbeddingError(f"Invalid JSON response: {str(e)}") from e

    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate text using LLM.

        Args:
            prompt: User prompt.
            system_prompt: System instruction.
            temperature: Temperature parameter (0.0 to 1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text.

        Raises:
            LLMGenerationError: If generation fails.

        """
        try:
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: dict[str, Any] = {
                "model": self.llm_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            resp = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout * 2,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            response = data.get("message", {}).get("content", "")

            if not response:
                raise LLMGenerationError("Empty response from Ollama")

            return response  # type: ignore[no-any-return]
        except httpx.TimeoutException as e:
            raise LLMGenerationError(f"Timeout generating text: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            raise LLMGenerationError(f"Request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise LLMGenerationError(f"Invalid JSON response: {str(e)}") from e

    def get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        delay: Optional[float] = None,
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts.

        Args:
            texts: List of input texts.
            batch_size: Number of texts per batch (kept for API compatibility).
            delay: Delay between requests in seconds.

        Returns:
            List of embedding vectors. Empty list for failed texts.

        """
        delay = delay or settings.OLLAMA_EMBED_DELAY
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
