"""Event Ingestion API Routes.

Defines HTTP endpoints for submitting raw signals and querying event state.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status

from app.api.dependencies import get_ingestion_service, get_event_repository
from app.api.schemas import IngestSignalRequest, SignalEventResponse
from app.ingestion.service import IngestionService
from app.storage.repositories import EventRepository

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post(
    "/ingest",
    response_model=SignalEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Raw Signal Event",
    description="Accepts webhook payloads or structured API signals, normalizes them, and checks for duplicates.",
)
async def ingest_event(
    request: Request,
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    tenant_id: str = Header(default="default", alias="X-Tenant-ID"),
    body: dict[str, Any] | None = None,
) -> SignalEventResponse:
    """Ingest a raw signal payload."""
    raw_body = body if body is not None else await request.json()
    headers_dict = dict(request.headers)

    # Extract payload if wrapped in IngestSignalRequest
    if "payload" in raw_body and isinstance(raw_body["payload"], dict):
        tenant_id = raw_body.get("tenant_id", tenant_id)
        payload_data = raw_body["payload"]
    else:
        payload_data = raw_body

    event, is_duplicate = await ingestion_service.process_signal(
        headers=headers_dict,
        payload=payload_data,
        tenant_id=tenant_id,
    )

    return SignalEventResponse(
        event_id=event.event_id,
        source_type=event.source_type,
        source_id=event.source_id,
        tenant_id=event.tenant_id,
        payload_hash=event.payload_hash,
        coalesce_key=event.coalesce_key,
        status=event.status.value,
        is_duplicate=is_duplicate,
        created_at=event.created_at,
        deadline_at=event.deadline_at,
    )


@router.get(
    "/{event_id}",
    response_model=SignalEventResponse,
    summary="Get Event by ID",
)
async def get_event(
    event_id: str,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> SignalEventResponse:
    """Retrieve an event by ID."""
    event = await event_repo.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found",
        )
    return SignalEventResponse(
        event_id=event.event_id,
        source_type=event.source_type,
        source_id=event.source_id,
        tenant_id=event.tenant_id,
        payload_hash=event.payload_hash,
        coalesce_key=event.coalesce_key,
        status=event.status.value,
        is_duplicate=False,
        created_at=event.created_at,
        deadline_at=event.deadline_at,
    )
