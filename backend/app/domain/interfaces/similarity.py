"""Semantic Similarity Provider Interface.

Defines protocol for comparing semantic similarity between two SignalEvent entities.
"""

from typing import Protocol
from app.domain.models import SignalEvent


class SemanticSimilarityProvider(Protocol):
    """Protocol for calculating semantic similarity scores between events."""

    async def compute_similarity(self, event1: SignalEvent, event2: SignalEvent) -> float:
        """Compute similarity score between 0.0 (unrelated) and 1.0 (identical)."""
        ...
