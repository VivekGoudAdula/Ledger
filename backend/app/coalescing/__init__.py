"""Coalescing package exports."""

from app.coalescing.fingerprint import DeterministicFingerprinter
from app.coalescing.similarity import DeterministicSimilarityProvider
from app.coalescing.service import CoalescingService

__all__ = [
    "DeterministicFingerprinter",
    "DeterministicSimilarityProvider",
    "CoalescingService",
]
