"""Recovery Domain Models.

Defines RecoveryOutcome telemetry dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RecoveryOutcome:
    """Telemetry report representing results of a failure recovery scan cycle."""

    scanned_pending_count: int = 0
    stale_candidates_count: int = 0
    reclaimed_count: int = 0
    already_completed_count: int = 0
    retried_count: int = 0
    failed_count: int = 0
    scan_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate recovery outcome timestamp."""
        if self.scan_timestamp and self.scan_timestamp.tzinfo is None:
            raise ValueError("scan_timestamp must be timezone-aware.")
