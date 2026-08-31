"""Scoring strategies for event evaluation."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from structlog import get_logger

from ..services import OllamaClient

logger = get_logger(__name__)


class ScoringStrategy(ABC):
    """Abstract base class for scoring strategies."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """Initialize with optional Ollama client."""
        self.ollama_client = ollama_client or OllamaClient()

    @abstractmethod
    def get_name(self) -> str:
        """Get strategy name."""
        pass

    @abstractmethod
    def get_prompt(self, event: Dict[str, Any]) -> str:
        """Get prompt for the strategy."""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data."""
        pass

    def score(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an event using the strategy.

        Args:
            event: Event data with title, content, etc.

        Returns:
            Dictionary with score and summary.

        """
        try:
            prompt = self.get_prompt(event)
            response = self.ollama_client.generate_text(prompt, temperature=0.3)

            # Log response for debugging
            logger.debug(
                f"{self.get_name()}_response",
                event_id=event.get("id"),
                response=response[:200],
            )

            result = self.parse_response(response)
            result["_raw_response"] = response

            return result

        except Exception as e:
            logger.error(
                f"{self.get_name()}_failed",
                event_id=event.get("id"),
                error=str(e),
            )
            return {
                "score": 0.0,
                "summary": f"Error: {str(e)}",
                "_error": str(e),
            }


class UrgencyScoring(ScoringStrategy):
    """Strategy for scoring event urgency."""

    def get_name(self) -> str:
        """Return strategy name."""
        return "urgency"

    def get_prompt(self, event: Dict[str, Any]) -> str:
        """Build prompt for urgency scoring."""
        return f"""
You are an analyst evaluating news urgency. Rate the urgency of this
event on a scale of 0.0 to 1.0.

Event title: {event.get("title", "N/A")}
Event content: {event.get("content", "N/A")[:1000]}

Consider:
- Time sensitivity (0.0 = not time-sensitive, 1.0 = requires immediate action)
- Impact severity (0.0 = minor impact, 1.0 = major impact)
- Scope (0.0 = local, 1.0 = global)

Respond in JSON format:
{{"score": 0.75, "summary": "Brief explanation of urgency rating"}}
""".strip()

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into urgency score.

        Args:
            response: Raw LLM response.

        Returns:
            Dictionary with score and summary.

        """
        try:
            # Try to extract JSON from response
            import re

            json_match = re.search(r"\{[^{}]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "score": float(data.get("score", 0.0)),
                    "summary": data.get("summary", "No summary provided"),
                }
            # Fallback: try to parse as JSON directly
            data = json.loads(response)
            return {
                "score": float(data.get("score", 0.0)),
                "summary": data.get("summary", "No summary provided"),
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(
                "urgency_parse_failed", response=response[:100], error=str(e)
            )
            return {
                "score": 0.0,
                "summary": "Failed to parse urgency score",
                "_parse_error": str(e),
            }


class ConflictScoring(ScoringStrategy):
    """Strategy for scoring event conflict potential."""

    def get_name(self) -> str:
        """Return strategy name."""
        return "conflict"

    def get_prompt(self, event: Dict[str, Any]) -> str:
        """Build prompt for conflict scoring."""
        return f"""
You are an analyst evaluating news for conflict potential.
Rate the conflict level of this event on a scale of 0.0 to 1.0.

Event title: {event.get("title", "N/A")}
Event content: {event.get("content", "N/A")[:1000]}

Consider:
- Presence of opposing viewpoints (0.0 = none, 1.0 = high)
- Tension or disagreement (0.0 = none, 1.0 = high)
- Potential for escalation (0.0 = none, 1.0 = high)

Respond in JSON format:
{{"score": 0.65, "summary": "Brief explanation of conflict rating"}}
""".strip()

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into conflict score.

        Args:
            response: Raw LLM response.

        Returns:
            Dictionary with score and summary.

        """
        try:
            import re

            json_match = re.search(r"\{[^{}]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "score": float(data.get("score", 0.0)),
                    "summary": data.get("summary", "No summary provided"),
                }
            data = json.loads(response)
            return {
                "score": float(data.get("score", 0.0)),
                "summary": data.get("summary", "No summary provided"),
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(
                "conflict_parse_failed", response=response[:100], error=str(e)
            )
            return {
                "score": 0.0,
                "summary": "Failed to parse conflict score",
                "_parse_error": str(e),
            }


class SurpriseScoring(ScoringStrategy):
    """Strategy for scoring event surprise factor."""

    def get_name(self) -> str:
        """Return strategy name."""
        return "surprise"

    def get_prompt(self, event: Dict[str, Any]) -> str:
        """Build prompt for surprise scoring."""
        return f"""
You are an analyst evaluating news for surprise factor. Rate how
surprising/unexpected this event is on a scale of 0.0 to 1.0.

Event title: {event.get("title", "N/A")}
Event content: {event.get("content", "N/A")[:1000]}

Consider:
- Deviation from expectations (0.0 = expected, 1.0 = highly unexpected)
- Novelty (0.0 = common, 1.0 = unprecedented)
- Contrast with normal patterns (0.0 = normal, 1.0 = shocking)

Respond in JSON format:
{{"score": 0.55, "summary": "Brief explanation of surprise rating"}}
""".strip()

    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into surprise score.

        Args:
            response: Raw LLM response.

        Returns:
            Dictionary with score and summary.

        """
        try:
            import re

            json_match = re.search(r"\{[^{}]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "score": float(data.get("score", 0.0)),
                    "summary": data.get("summary", "No summary provided"),
                }
            data = json.loads(response)
            return {
                "score": float(data.get("score", 0.0)),
                "summary": data.get("summary", "No summary provided"),
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(
                "surprise_parse_failed", response=response[:100], error=str(e)
            )
            return {
                "score": 0.0,
                "summary": "Failed to parse surprise score",
                "_parse_error": str(e),
            }
