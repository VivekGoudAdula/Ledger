"""SQLAlchemy ORM Schemas for Ledger Persistence.

Maps domain entities to relational database tables with proper indexing.
"""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class EventORM(Base):
    """Database model for SignalEvent entities."""

    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    coalesce_key: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    
    event_type: Mapped[str] = mapped_column(String(100), default="generic_event", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Valuation & Admission columns
    urgency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    consequence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_compute_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    admission_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    admission_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    admission_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Queue & Worker Lease columns
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Coalescing metadata
    coalesced_into_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    coalesced_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_tenant_hash", "tenant_id", "payload_hash", unique=True),
        Index("idx_queue_priority", "status", "admission_score"),
    )


class IncidentORM(Base):
    """Database model for CoalescedIncident entities."""

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    coalesce_key: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    representative_title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    coalescing_method: Mapped[str] = mapped_column(String(50), nullable=False)
    
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        Index("idx_incident_candidate", "tenant_id", "coalesce_key", "last_seen"),
    )


class IncidentSignalLinkORM(Base):
    """Association table linking original SignalEvents to a CoalescedIncident."""

    __tablename__ = "incident_signal_links"

    link_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.event_id"), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ValueAssessmentORM(Base):
    """Database model for ValueAssessment entities."""

    __tablename__ = "value_assessments"

    assessment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    work_item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    urgency: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    consequence_of_drop: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_compute_cost: Mapped[float] = mapped_column(Float, nullable=False)
    expected_value: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    value_per_compute: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    estimator: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class ExecutionCheckpointORM(Base):
    """Database model for worker execution checkpoints."""

    __tablename__ = "execution_checkpoints"

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    worker_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[str] = mapped_column(String(30), default="PROCESSING", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ExecutionResultORM(Base):
    """Database model for durable worker execution results."""

    __tablename__ = "execution_results"

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class IdempotencyRecordORM(Base):
    """Database model for database-enforced logical execution idempotency records."""

    __tablename__ = "idempotency_records"

    idempotency_key: Mapped[str] = mapped_column(String(180), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    work_item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS", nullable=False, index=True)
    execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    result_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_idempotency_unique", "tenant_id", "work_item_id", "action_type", unique=True),
    )
