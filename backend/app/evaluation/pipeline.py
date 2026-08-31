"""Evaluation pipeline for processing events through multiple strategies."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from structlog import get_logger

from ..models import Event
from .strategies import ScoringStrategy

logger = get_logger(__name__)


class EvaluationPipeline:
    """Pipeline for evaluating events using multiple scoring strategies."""

    def __init__(self, strategies: Optional[List[ScoringStrategy]] = None):
        """
        Initialize evaluation pipeline with strategies.

        Args:
            strategies: List of scoring strategies. If None, uses default strategies.

        """
        self.strategies = strategies or []

    def add_strategy(self, strategy: ScoringStrategy) -> None:
        """Add a strategy to the pipeline."""
        self.strategies.append(strategy)

    def evaluate_event(self, event: Event) -> Dict[str, Any]:
        """
        Evaluate a single event using all strategies.

        Args:
            event: Event to evaluate.

        Returns:
            Dictionary with evaluation results for all strategies.

        """
        event_dict = {
            "id": event.id,
            "title": event.title,
            "content": event.content,
            "source_url": event.source_url,
            "published_at": event.published_at.isoformat()
            if event.published_at
            else None,
        }

        results = {}
        summaries = []

        for strategy in self.strategies:
            name = strategy.get_name()
            logger.info(
                "strategy_started",
                strategy=name,
                event_id=event.id,
            )

            result = strategy.score(event_dict)

            # Store results
            results[name] = {
                "score": result.get("score", 0.0),
                "summary": result.get("summary", ""),
            }
            summaries.append(f"{name}: {result.get('summary', '')}")

            logger.info(
                "strategy_completed",
                strategy=name,
                event_id=event.id,
                score=result.get("score", 0.0),
            )

        # Combine summaries
        combined_summary = " | ".join(summaries)

        return {
            "results": results,
            "combined_summary": combined_summary,
            "pipeline_version": "1.0",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def evaluate_events(
        self,
        events: List[Event],
        batch_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple events.

        Args:
            events: List of events to evaluate.
            batch_size: Number of events per batch (for logging).

        Returns:
            List of evaluation results.

        """
        results = []
        total = len(events)

        for i, event in enumerate(events):
            logger.info(
                "evaluation_progress",
                current=i + 1,
                total=total,
                event_id=event.id,
            )

            result = self.evaluate_event(event)
            results.append(result)

        return results
