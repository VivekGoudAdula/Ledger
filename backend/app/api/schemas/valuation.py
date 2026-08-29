"""API Schemas for Signal Valuation.

Defines Pydantic models for valuation requests and structured ValueAssessment responses.
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AssessWorkItemRequest(BaseModel):
    """Request schema for initiating work item valuation."""

    work_item_id: str = Field(..., description="ID of SignalEvent or CoalescedIncident to evaluate")
    work_item_type: str = Field(default="signal", description="Type of work item: 'signal' or 'incident'")


class ValueAssessmentResponse(BaseModel):
    """Response schema representing structured ValueAssessment output."""

    assessment_id: str
    work_item_id: str
    work_item_type: str
    urgency: float
    confidence: float
    consequence_of_drop: float
    estimated_compute_cost: float
    expected_value: float
    value_per_compute: float
    rationale: str
    estimator: str
    policy_version: str
    is_fallback: bool
    deadline: datetime | None = None
    estimated_at: datetime

    model_config = ConfigDict(from_attributes=True)
