"""Admission Domain Models.

Defines CapacityState, TenantState, and AdmissionDecision domain entities.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason


@dataclass
class CapacityState:
    """Represents real-time system compute capacity and active workload metrics."""

    total_capacity: float = 100.0
    available_capacity: float = 100.0
    active_compute: float = 0.0
    active_work_items: int = 0

    def __post_init__(self) -> None:
        """Validate numeric capacity constraints."""
        for name, val in [
            ("total_capacity", self.total_capacity),
            ("available_capacity", self.available_capacity),
            ("active_compute", self.active_compute),
        ]:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise ValueError(f"Capacity field '{name}' must be a finite float.")
            if val < 0.0:
                raise ValueError(f"Capacity field '{name}' cannot be negative, got {val}.")

        if self.total_capacity <= 0.0:
            raise ValueError("total_capacity must be greater than zero.")
        if self.available_capacity > self.total_capacity:
            raise ValueError(f"available_capacity ({self.available_capacity}) cannot exceed total_capacity ({self.total_capacity}).")


@dataclass
class TenantState:
    """Represents tenant resource usage, quota limits, and fair-share weights."""

    tenant_id: str
    current_usage: float = 0.0
    quota: float = 50.0
    weight: float = 1.0

    def __post_init__(self) -> None:
        """Validate tenant quota parameters."""
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValueError("TenantState tenant_id must be a non-empty string.")
        if self.current_usage < 0.0:
            raise ValueError("current_usage cannot be negative.")
        if self.quota <= 0.0:
            raise ValueError("quota must be greater than zero.")


@dataclass
class AdmissionDecision:
    """Structured decision output produced by the deterministic AdmissionController."""

    decision: AdmissionDecisionEnum
    work_item_id: str
    reason: AdmissionReason
    effective_value: float
    value_per_compute: float
    capacity_required: float
    capacity_available: float
    tenant_id: str
    explanation: str
    policy_version: str = "admission_policy_v1"
    defer_until: datetime | None = None
    decision_id: str = field(default_factory=lambda: f"DEC-{uuid.uuid4().hex[:8]}")
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate decision fields and timezone awareness."""
        if not self.work_item_id or not isinstance(self.work_item_id, str):
            raise ValueError("AdmissionDecision work_item_id must be a non-empty string.")
        if self.evaluated_at and self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at timestamp must be timezone-aware.")
        if self.defer_until and self.defer_until.tzinfo is None:
            raise ValueError("defer_until timestamp must be timezone-aware.")
