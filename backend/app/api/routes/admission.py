"""Admission Control API Routes.

Defines HTTP endpoints for evaluating deterministic work item admission decisions.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_event_repository,
    get_incident_repository,
    get_valuation_service,
    get_admission_controller,
)
from app.api.schemas import EvaluateAdmissionRequest, AdmissionDecisionResponse
from app.domain.models import CapacityState, TenantState
from app.storage.repositories import EventRepository, IncidentRepository
from app.valuation.service import ValueEstimationService
from app.admission.controller import AdmissionController

router = APIRouter(prefix="/api/v1/admission", tags=["admission"])


@router.post(
    "/evaluate",
    response_model=AdmissionDecisionResponse,
    summary="Evaluate Admission Decision for Work Item",
)
async def evaluate_admission(
    request: EvaluateAdmissionRequest,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    valuation_service: Annotated[ValueEstimationService, Depends(get_valuation_service)],
    admission_controller: Annotated[AdmissionController, Depends(get_admission_controller)],
) -> AdmissionDecisionResponse:
    """Evaluate deterministic admission decision (ADMIT, DEFER, SHED) for a work item against capacity."""
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

    # Step 1: Obtain ValueAssessment from valuation service
    assessment = await valuation_service.assess_work_item(work_item)

    # Step 2: Construct CapacityState & TenantState context
    capacity = CapacityState(
        total_capacity=request.total_capacity,
        available_capacity=request.available_capacity,
    )
    tenant = TenantState(
        tenant_id=work_item.tenant_id,
        current_usage=request.tenant_current_usage,
        quota=request.tenant_quota,
    )

    # Step 3: Evaluate deterministic admission decision
    decision = admission_controller.evaluate_admission(
        work_item=work_item,
        assessment=assessment,
        capacity=capacity,
        tenant=tenant,
    )

    return AdmissionDecisionResponse.model_validate(decision)
