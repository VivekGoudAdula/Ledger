"""Incident & Coalescing Telemetry API Routes.

Defines HTTP endpoints for querying coalesced incidents, original linked signals, and metrics.
"""

from typing import Annotated, Sequence
from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.api.dependencies import get_incident_repository
from app.api.schemas import CoalescedIncidentResponse, SignalEventResponse, CoalescingMetricsResponse
from app.storage.repositories import IncidentRepository

router = APIRouter(prefix="/api/v1", tags=["incidents"])


@router.get(
    "/incidents/{incident_id}",
    response_model=CoalescedIncidentResponse,
    summary="Get Coalesced Incident by ID",
)
async def get_incident(
    incident_id: str,
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
) -> CoalescedIncidentResponse:
    """Retrieve a coalesced incident by ID."""
    incident = await incident_repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coalesced Incident '{incident_id}' not found",
        )
    return CoalescedIncidentResponse(
        incident_id=incident.incident_id,
        tenant_id=incident.tenant_id,
        coalesce_key=incident.coalesce_key,
        representative_title=incident.representative_title,
        source_types=incident.source_types,
        signal_count=incident.signal_count,
        coalescing_method=incident.coalescing_method,
        event_ids=incident.event_ids,
        first_seen=incident.first_seen,
        last_seen=incident.last_seen,
        created_at=incident.created_at,
    )


@router.get(
    "/incidents/{incident_id}/signals",
    response_model=list[SignalEventResponse],
    summary="Get Original Signals Linked to Incident",
)
async def get_incident_signals(
    incident_id: str,
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
) -> list[SignalEventResponse]:
    """Retrieve all original SignalEvents linked to a coalesced incident."""
    incident = await incident_repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coalesced Incident '{incident_id}' not found",
        )

    signals = await incident_repo.get_signals_for_incident(incident_id)
    return [
        SignalEventResponse(
            event_id=sig.event_id,
            source_type=sig.source_type,
            source_id=sig.source_id,
            tenant_id=sig.tenant_id,
            event_type=sig.event_type,
            severity=sig.severity.value,
            payload_hash=sig.payload_hash,
            coalesce_key=sig.coalesce_key,
            status=sig.status.value,
            is_duplicate=False,
            metadata=sig.metadata,
            created_at=sig.created_at,
            deadline_at=sig.deadline_at,
        )
        for sig in signals
    ]


@router.get(
    "/coalescing/metrics",
    response_model=CoalescingMetricsResponse,
    summary="Get Coalescing Performance Telemetry",
)
async def get_coalescing_metrics(
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    tenant_id: str = Header(default="default", alias="X-Tenant-ID"),
) -> CoalescingMetricsResponse:
    """Retrieve coalescing ratio and aggregate incident statistics for a tenant."""
    metrics = await incident_repo.get_metrics_summary(tenant_id=tenant_id)
    return CoalescingMetricsResponse(
        tenant_id=tenant_id,
        signals_received=int(metrics["signals_received"]),
        signals_coalesced=int(metrics["signals_coalesced"]),
        incidents_created=int(metrics["incidents_created"]),
        coalescing_ratio=float(metrics["coalescing_ratio"]),
        avg_signals_per_incident=float(metrics["avg_signals_per_incident"]),
    )
