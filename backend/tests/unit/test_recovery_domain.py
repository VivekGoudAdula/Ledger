"""Unit Tests for Recovery Domain Entities.

Validates RecoveryOutcome dataclass and field boundaries.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import RecoveryOutcome


def test_valid_recovery_outcome_construction():
    outcome = RecoveryOutcome(
        scanned_pending_count=5,
        stale_candidates_count=2,
        reclaimed_count=2,
        already_completed_count=1,
        retried_count=1,
        failed_count=0,
    )
    assert outcome.scanned_pending_count == 5
    assert outcome.already_completed_count == 1
    assert outcome.scan_timestamp.tzinfo == timezone.utc
