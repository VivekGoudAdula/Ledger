"""Domain Enumerations for Ledger.

Defines core business states, admission decisions, classification enums, and severity levels.
"""

from enum import Enum


class EventStatus(str, Enum):
    """Lifecycle state machine for a SignalEvent."""

    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    COALESCED = "COALESCED"
    VALUED = "VALUED"
    ADMITTED = "ADMITTED"
    DEFERRED = "DEFERRED"
    SHED = "SHED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRY = "RETRY"


class EventSource(str, Enum):
    """Canonical event source category."""

    GITHUB = "github"
    INCIDENT = "incident"
    TELEMETRY = "telemetry"
    SYSTEM = "system"
    GENERIC = "generic_api"


class SeverityLevel(str, Enum):
    """Canonical severity level of an incoming signal event."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AdmissionDecision(str, Enum):
    """Deterministic admission controller decision outcomes."""

    ADMIT = "ADMIT"
    DEFER = "DEFER"
    SHED = "SHED"


# Alias for backward compatibility
DecisionType = AdmissionDecision


class UrgencyLevel(str, Enum):
    """Qualitative urgency levels mapped to numeric scores."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"


class AdmissionReason(str, Enum):
    """Reason codes explaining deterministic admission decisions."""

    ADMITTED_CAPACITY_AVAILABLE = "ADMITTED_CAPACITY_AVAILABLE"
    ADMITTED_HIGH_VALUE = "ADMITTED_HIGH_VALUE"
    DEFERRED_CAPACITY_EXHAUSTED = "DEFERRED_CAPACITY_EXHAUSTED"
    DEFERRED_TENANT_QUOTA = "DEFERRED_TENANT_QUOTA"
    SHED_LOW_VALUE_DURING_OVERLOAD = "SHED_LOW_VALUE_DURING_OVERLOAD"
    SHED_DEADLINE_EXPIRED = "SHED_DEADLINE_EXPIRED"
    SHED_BELOW_VALUE_FLOOR = "SHED_BELOW_VALUE_FLOOR"
    REJECTED_INVALID_INPUT = "REJECTED_INVALID_INPUT"
    COALESCED_DUPLICATE = "COALESCED_DUPLICATE"


class ActionType(str, Enum):
    """Canonical logical action types executed by workers."""

    ANALYZE_SIGNAL = "ANALYZE_SIGNAL"
    AGGREGATE_INCIDENT = "AGGREGATE_INCIDENT"
    PROCESS_ALERT = "PROCESS_ALERT"
    GENERIC_ACTION = "GENERIC_ACTION"


class IdempotencyStatus(str, Enum):
    """Idempotency record lifecycle states."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    IDEMPOTENCY_HIT = "IDEMPOTENCY_HIT"
