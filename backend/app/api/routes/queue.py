"""Queue Transport & Telemetry API Routes.

Defines HTTP endpoints for evaluating admission, enqueuing admitted work, and querying broker metrics.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_event_repository,
    get_incident_repository,
    get_valuation_service,
    get_admission_controller,
    get_queue_broker,
    get_queue_publisher_service,
)
from app.api.schemas import PublishWorkRequest, PublishWorkResponse, QueueMetricsResponse, QueueMessageResponse
from app.domain.models import CapacityState, TenantState
from app.domain.interfaces.queue import WorkQueueInterface
from app.storage.repositories import EventRepository, IncidentRepository
from app.valuation.service import ValueEstimationService
from app.admission.controller import AdmissionController
from app.queue.service import QueuePublisherService

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


@router.post(
    "/publish",
    response_model=PublishWorkResponse,
    summary="Evaluate Admission and Enqueue Admitted Work",
)
async def publish_work_item(
    request: PublishWorkRequest,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    valuation_service: Annotated[ValueEstimationService, Depends(get_valuation_service)],
    admission_controller: Annotated[AdmissionController, Depends(get_admission_controller)],
    publisher_service: Annotated[QueuePublisherService, Depends(get_queue_publisher_service)],
) -> PublishWorkResponse:
    """Evaluate admission decision for work item and publish to queue broker if ADMITTED."""
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

    # Step 1: Assess Value
    assessment = await valuation_service.assess_work_item(work_item)

    # Step 2: Evaluate Admission
    capacity = CapacityState(total_capacity=100.0, available_capacity=100.0)
    tenant = TenantState(tenant_id=work_item.tenant_id)
    decision = admission_controller.evaluate_admission(work_item, assessment, capacity, tenant)

    # Step 3: Handle Admission Transport Routing (Enqueues ONLY if ADMIT)
    final_status, msg = await publisher_service.handle_admission_decision(work_item, decision)

    msg_resp = QueueMessageResponse.model_validate(msg) if msg else None

    return PublishWorkResponse(
        work_item_id=request.work_item_id,
        status=final_status.value,
        decision=decision.decision.value,
        message=msg_resp,
    )


@router.get(
    "/metrics",
    response_model=QueueMetricsResponse,
    summary="Get Queue Depth and Telemetry Metrics",
)
async def get_queue_metrics(
    broker: Annotated[WorkQueueInterface, Depends(get_queue_broker)],
) -> QueueMetricsResponse:
    """Retrieve queue length, pending message count, and active consumer statistics."""
    metrics = await broker.get_metrics()
    return QueueMetricsResponse.model_validate(metrics)
