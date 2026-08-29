"""Signal Valuation API Routes.

Defines HTTP endpoints for initiating work item value estimation and querying assessments.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_event_repository,
    get_incident_repository,
    get_valuation_repository,
    get_valuation_service,
)
from app.api.schemas import AssessWorkItemRequest, ValueAssessmentResponse
from app.storage.repositories import EventRepository, IncidentRepository, ValuationRepository
from app.valuation.service import ValueEstimationService

router = APIRouter(prefix="/api/v1/valuation", tags=["valuation"])


@router.post(
    "/assess",
    response_model=ValueAssessmentResponse,
    summary="Assess Expected Value of Signal or Incident",
)
async def assess_work_item(
    request: AssessWorkItemRequest,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    valuation_service: Annotated[ValueEstimationService, Depends(get_valuation_service)],
) -> ValueAssessmentResponse:
    """Evaluate value dimensions (urgency, confidence, consequence, compute cost) for a work item."""
    work_item = None
    if request.work_item_type == "signal":
        work_item = await event_repo.get_by_id(request.work_item_id)
    elif request.work_item_type == "incident":
        work_item = await incident_repo.get_by_id(request.work_item_id)

    if not work_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{request.work_item_type.capitalize()} '{request.work_item_id}' not found",
        )

    assessment = await valuation_service.assess_work_item(work_item)
    return ValueAssessmentResponse.model_validate(assessment)


@router.get(
    "/assessments/{work_item_id}",
    response_model=ValueAssessmentResponse,
    summary="Get Stored Value Assessment by Work Item ID",
)
async def get_assessment(
    work_item_id: str,
    valuation_repo: Annotated[ValuationRepository, Depends(get_valuation_repository)],
) -> ValueAssessmentResponse:
    """Fetch the latest stored ValueAssessment for a work item."""
    assessment = await valuation_repo.get_latest_assessment(work_item_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored value assessment found for work item '{work_item_id}'",
        )
    return ValueAssessmentResponse.model_validate(assessment)
