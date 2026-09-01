"""Insight generation service with multi-stage LLM prompting."""

from typing import Any, Dict, List, Optional, Tuple

from structlog import get_logger

from ..models import Event
from ..services import OllamaClient

logger = get_logger(__name__)


class InsightGenerator:
    """Service for generating dialectical insights from events."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize insight generator.

        Args:
            ollama_client: Optional Ollama client. Creates default if not provided.

        """
        self.ollama_client = ollama_client or OllamaClient()

    def _get_analyst_prompt(self, events: List[Dict[str, Any]]) -> str:
        """Build prompt for the analyst stage."""
        events_text = "\n\n".join(
            [
                f"Event {i + 1}: {e.get('title', 'N/A')}\n"
                f"Content: {e.get('content', 'N/A')[:500]}\n"
                f"Urgency: {e.get('urgency', 0):.2f}, "
                f"Conflict: {e.get('conflict', 0):.2f}, "
                f"Surprise: {e.get('surprise', 0):.2f}"
                for i, e in enumerate(events)
            ]
        )

        return f"""
You are an analytical expert. Analyze the following events and
provide a comprehensive synthesis.

Events:
{events_text}

Provide your analysis in the following format:
1. **Key Themes**: Identify 3-5 main themes emerging from these events
2. **Patterns**: Identify any patterns, trends, or recurring elements
3. **Implications**: What are the potential implications or consequences?
4. **Contradictions**: Note any contradictions or tensions between events

Your analysis should be insightful, balanced, and well-structured.
""".strip()

    def _get_skeptic_prompt(self, analyst_analysis: str) -> str:
        """Build prompt for the skeptic stage."""
        return f"""
You are a skeptical critic. Review the following analysis and challenge it.

Analysis to critique:
{analyst_analysis}

Provide a critique that:
1. **Challenge assumptions**: What assumptions might be flawed?
2. **Alternative interpretations**: What other ways to interpret the data?
3. **Weaknesses**: What are the weaknesses in the analysis?
4. **Missing perspectives**: What perspectives or information are missing?

Your critique should be constructive, specific, and thoughtful.
""".strip()

    def _get_synthesis_prompt(
        self,
        analyst_analysis: str,
        skeptic_critique: str,
    ) -> str:
        """Build prompt for the synthesis stage."""
        return f"""
You are a synthesizer. Integrate the analysis and critique into a
balanced, dialectical synthesis.

Analysis:
{analyst_analysis}

Critique:
{skeptic_critique}

Provide a synthesis that:
1. **Reconciles**: Integrate the analysis and critique into a coherent whole
2. **Key insight**: Distill the most important insight
3. **Nuanced conclusion**: Provide a balanced, nuanced conclusion
4. **Actionable takeaway**: What is the key takeaway for decision-makers?

Your synthesis should be insightful, balanced, and actionable.
""".strip()

    def _parse_stage_response(self, response: str) -> Tuple[str, str]:
        """
        Parse stage response to extract content and any structured data.

        Returns:
            Tuple of (content, raw_response)

        """
        return response.strip(), response

    async def generate_insight(
        self,
        events: List[Event],
        scores: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a dialectical insight from a list of events.

        Args:
            events: List of events to synthesize.
            scores: List of score dictionaries for each event.

        Returns:
            Dictionary with stages and final insight.

        """
        if not events or not scores or len(events) != len(scores):
            raise ValueError("Events and scores must be non-empty and same length")

        # Prepare event data with scores
        event_data = []
        for i, event in enumerate(events):
            score_data = scores[i] if i < len(scores) else {}
            event_data.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "content": event.content,
                    "urgency": score_data.get("urgency", 0.0),
                    "conflict": score_data.get("conflict", 0.0),
                    "surprise": score_data.get("surprise", 0.0),
                    "evaluation": event.evaluation_data,
                }
            )

        logger.info(
            "insight_generation_started",
            event_count=len(event_data),
        )

        stages = {}

        # Stage 1: Analyst
        logger.debug("insight_stage_analyst_started")
        analyst_prompt = self._get_analyst_prompt(event_data)
        analyst_response = self.ollama_client.generate_text(
            analyst_prompt,
            temperature=0.5,
            max_tokens=2000,
        )
        analyst_content, analyst_raw = self._parse_stage_response(analyst_response)
        stages["analyst"] = {
            "content": analyst_content,
            "raw": analyst_raw,
        }
        logger.debug("insight_stage_analyst_completed", length=len(analyst_content))

        # Stage 2: Skeptic
        logger.debug("insight_stage_skeptic_started")
        skeptic_prompt = self._get_skeptic_prompt(analyst_content)
        skeptic_response = self.ollama_client.generate_text(
            skeptic_prompt,
            temperature=0.5,
            max_tokens=1500,
        )
        skeptic_content, skeptic_raw = self._parse_stage_response(skeptic_response)
        stages["skeptic"] = {
            "content": skeptic_content,
            "raw": skeptic_raw,
        }
        logger.debug("insight_stage_skeptic_completed", length=len(skeptic_content))

        # Stage 3: Synthesis
        logger.debug("insight_stage_synthesis_started")
        synthesis_prompt = self._get_synthesis_prompt(
            analyst_content,
            skeptic_content,
        )
        synthesis_response = self.ollama_client.generate_text(
            synthesis_prompt,
            temperature=0.3,
            max_tokens=1500,
        )
        synthesis_content, synthesis_raw = self._parse_stage_response(
            synthesis_response
        )
        stages["synthesis"] = {
            "content": synthesis_content,
            "raw": synthesis_raw,
        }
        logger.debug("insight_stage_synthesis_completed", length=len(synthesis_content))

        logger.info(
            "insight_generation_completed",
            event_count=len(event_data),
            total_length=len(synthesis_content),
        )

        return {
            "stages": stages,
            "content": synthesis_content,
            "event_ids": [e.id for e in events],
            "event_count": len(events),
        }

    def select_top_events(
        self,
        events: List[Event],
        scores: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> Tuple[List[Event], List[Dict[str, Any]]]:
        """
        Select top K events based on composite score (conflict + urgency).

        Args:
            events: List of events.
            scores: List of score dictionaries.
            top_k: Number of events to select.

        Returns:
            Tuple of (selected_events, selected_scores).

        """
        if not events or not scores:
            return [], []

        # Calculate composite score for each event
        scored = []
        for i, (event, score) in enumerate(zip(events, scores)):
            urgency = score.get("urgency", 0.0)
            conflict = score.get("conflict", 0.0)
            surprise = score.get("surprise", 0.0)
            composite = conflict + urgency + (surprise * 0.5)
            scored.append(
                {
                    "index": i,
                    "event": event,
                    "score": score,
                    "composite": composite,
                }
            )

        # Sort by composite score descending
        scored.sort(key=lambda x: x["composite"], reverse=True)

        # Select top K
        selected = scored[:top_k]

        selected_events = [item["event"] for item in selected]
        selected_scores = [item["score"] for item in selected]

        logger.info(
            "top_events_selected",
            top_k=top_k,
            selected_count=len(selected_events),
        )

        return selected_events, selected_scores
