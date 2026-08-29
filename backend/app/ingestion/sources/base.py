"""Base Source Adapter Abstract Class.

Abstract base class for all signal source payload converters.
"""

from abc import ABC, abstractmethod
from typing import Any
from app.domain.models import SignalEvent


class BaseSourceAdapter(ABC):
    """Abstract Base Class for Signal Source Adapters."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source identifier string (e.g. 'github', 'incident')."""
        ...

    @abstractmethod
    def can_handle(self, headers: dict[str, str], payload: dict[str, Any]) -> bool:
        """Determine if this adapter can process the given request payload/headers."""
        ...

    @abstractmethod
    def parse_raw(self, headers: dict[str, str], payload: dict[str, Any], tenant_id: str) -> SignalEvent:
        """Parse raw payload into a canonical SignalEvent entity."""
        ...
