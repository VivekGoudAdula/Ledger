"""ValueAssessment Domain Entity.

Represents structured, explainable value estimation for a signal or incident.
Enforces score validation and provides deterministic calculation helper formulas.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ValueAssessment:
    """Structured valuation output for work items (SignalEvents or CoalescedIncidents)."""

    work_item_id: str
    work_item_type: str  # "signal" or "incident"
    urgency: float
    confidence: float
    consequence_of_drop: float
    estimated_compute_cost: float
    rationale: str
    estimator: str = "rule_based_v1"
    policy_version: str = "v1.0"
    is_fallback: bool = False
    deadline: datetime | None = None
    expected_value: float = 0.0
    value_per_compute: float = 0.0
    assessment_id: str = field(default_factory=lambda: f"VAL-{uuid.uuid4().hex[:8]}")
    estimated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate all numeric score bounds, types, and timezone-aware timestamps."""
        if not self.work_item_id or not isinstance(self.work_item_id, str):
            raise ValueError("ValueAssessment work_item_id must be a non-empty string.")

        if self.work_item_type not in ("signal", "incident"):
            raise ValueError("work_item_type must be either 'signal' or 'incident'.")

        self.urgency = self._validate_score("urgency", self.urgency)
        self.confidence = self._validate_score("confidence", self.confidence)
        self.consequence_of_drop = self._validate_score("consequence_of_drop", self.consequence_of_drop)

        # Validate compute cost: finite, positive, non-zero
        if not isinstance(self.estimated_compute_cost, (int, float)) or math.isnan(self.estimated_compute_cost) or math.isinf(self.estimated_compute_cost):
            raise ValueError("estimated_compute_cost must be a finite numeric value.")
        if self.estimated_compute_cost <= 0.0:
            raise ValueError("estimated_compute_cost must be greater than zero.")

        # Ensure timestamps are timezone-aware
        if self.estimated_at and self.estimated_at.tzinfo is None:
            raise ValueError("estimated_at timestamp must be timezone-aware.")
        if self.deadline and self.deadline.tzinfo is None:
            raise ValueError("deadline timestamp must be timezone-aware.")

    def _validate_score(self, name: str, value: float) -> float:
        """Enforce normalized float bound check [0.0, 1.0]."""
        if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
            raise ValueError(f"{name} must be a finite float, got {value}.")
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{name} must be within bounds [0.0, 1.0], got {value}.")
        return float(value)

    @staticmethod
    def compute_expected_value(
        urgency: float,
        confidence: float,
        consequence_of_drop: float,
        deadline: datetime | None = None,
        created_at: datetime | None = None,
        reference_time: datetime | None = None,
    ) -> float:
        """Compute deterministic expected_value from validated dimension scores and freshness.

        Formula:
            Importance = (urgency * 0.35) + (consequence_of_drop * 0.45)
            BaseValue = Importance * (0.50 + 0.50 * confidence)
            Freshness = Deadline Decay Ratio (1.0 if no deadline or before deadline)
            expected_value = round(BaseValue * Freshness, 4)
        """
        importance = (urgency * 0.35) + (consequence_of_drop * 0.45)
        base_value = importance * (0.50 + (0.50 * confidence))

        freshness = 1.0
        if deadline:
            now = reference_time or datetime.now(timezone.utc)
            if now >= deadline:
                freshness = 0.0
            elif created_at and deadline > created_at:
                total_duration = (deadline - created_at).total_seconds()
                remaining = (deadline - now).total_seconds()
                freshness = max(0.0, min(1.0, remaining / total_duration))

        return round(max(0.0, min(1.0, base_value * freshness)), 4)

    @staticmethod
    def compute_value_per_compute(expected_value: float, estimated_compute_cost: float) -> float:
        """Compute deterministic value_per_compute ratio.

        Formula:
            value_per_compute = round(expected_value / max(estimated_compute_cost, 0.01), 4)
        """
        safe_cost = max(estimated_compute_cost, 0.01)
        return round(expected_value / safe_cost, 4)
