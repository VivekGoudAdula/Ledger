"""Deterministic & Rule-Based Similarity Provider.

Provides optional semantic keyword overlap comparison without requiring external LLM/AI dependencies.
"""

from app.domain.models import SignalEvent
from app.domain.interfaces.similarity import SemanticSimilarityProvider


class DeterministicSimilarityProvider(SemanticSimilarityProvider):
    """Calculates keyword Jaccard similarity between two events for optional semantic matching."""

    async def compute_similarity(self, event1: SignalEvent, event2: SignalEvent) -> float:
        """Compute keyword Jaccard similarity index between two events."""
        if event1.tenant_id != event2.tenant_id:
            return 0.0

        words1 = self._tokenize(event1)
        words2 = self._tokenize(event2)

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return round(intersection / union, 4) if union > 0 else 0.0

    def _tokenize(self, event: SignalEvent) -> set[str]:
        """Tokenize event title, category, and metadata into lowercased terms."""
        terms = [event.source_type, event.event_type, event.coalesce_key]
        if event.metadata:
            for k, v in event.metadata.items():
                if isinstance(v, str):
                    terms.append(v)
        
        raw_text = " ".join(terms).lower()
        # Simple whitespace tokenizer excluding common stop words
        words = {w.strip(".,_-:;") for w in raw_text.split() if len(w) > 2}
        return words
