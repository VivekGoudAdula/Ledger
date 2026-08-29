"""API Schemas for Admission Control.

Defines Pydantic models for evaluation requests and AdmissionDecision responses.
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.domain.enums import AdmissionDecision as AdmissionDecisionEnum, AdmissionReason


class EvaluateAdmissionRequest(BaseModel):
    """Request schema for evaluating admission decision."""

    work_item_id: str = Field(..., description="ID of SignalEvent or CoalescedIncident to evaluate")
    work_item_type: str = Field(default="signal", description="Type of work item: 'signal' or 'incident'")
    available_capacity: float = Field(default=100.0, ge=0.0, description="Current available compute capacity units")
    total_capacity: float = Field(default=100.0, gt=0.0, description="Total system capacity units")
    tenant_quota: float = Field(default=50.0, gt=0.0, description="Tenant reserved compute quota limit")
    tenant_current_usage: float = Field(default=0.0, ge=0.0, description="Current tenant compute usage")


class AdmissionDecisionResponse(BaseModel):
    """Response schema representing structured AdmissionDecision output."""

    decision_id: str
    decision: AdmissionDecisionEnum
    work_item_id: str
    reason: AdmissionReason
    effective_value: float
    value_per_compute: float
    capacity_required: float
    capacity_available: float
    tenant_id: str
    explanation: str
    policy_version: str
    defer_until: datetime | None = None
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
