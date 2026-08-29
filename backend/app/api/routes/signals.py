"""Signal Ingestion API Routes.

Exposes POST /signals endpoint for incoming signal normalization and persistence.
"""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status

from app.api.dependencies import get_ingestion_service, get_event_repository
from app.api.schemas import SignalEventResponse
from app.ingestion.service import IngestionService
from app.storage.repositories import EventRepository

router = APIRouter(tags=["signals"])

# Request payload maximum size limit (2MB)
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024


@router.post(
    "/signals",
    response_model=SignalEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Incoming Signal Event",
    description="Accepts webhook payloads or structured API signals, normalizes them, and persists canonical events.",
)
@router.post(
    "/api/v1/events/ingest",
    response_model=SignalEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Signal Event (Alias)",
)
async def ingest_signal(
    request: Request,
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
    tenant_id: str = Header(default="default", alias="X-Tenant-ID"),
    body: dict[str, Any] | None = None,
) -> SignalEventResponse:
    """Ingest a raw signal payload with size limit validation."""
    # Check payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size exceeds 2MB limit",
        )

    try:
        raw_body = body if body is not None else await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {exc}",
        )

    headers_dict = dict(request.headers)

    # Extract payload if wrapped in IngestSignalRequest wrapper
    if "payload" in raw_body and isinstance(raw_body["payload"], dict):
        tenant_id = raw_body.get("tenant_id", tenant_id)
        payload_data = raw_body["payload"]
    else:
        payload_data = raw_body

    try:
        event, is_duplicate = await ingestion_service.process_signal(
            headers=headers_dict,
            payload=payload_data,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Signal validation error: {exc}",
        )

    return SignalEventResponse(
        event_id=event.event_id,
        source_type=event.source_type,
        source_id=event.source_id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        severity=event.severity.value,
        payload_hash=event.payload_hash,
        coalesce_key=event.coalesce_key,
        status=event.status.value,
        is_duplicate=is_duplicate,
        metadata=event.metadata,
        created_at=event.created_at,
        deadline_at=event.deadline_at,
    )


@router.get(
    "/api/v1/events/{event_id}",
    response_model=SignalEventResponse,
    summary="Get Event by ID",
)
async def get_event(
    event_id: str,
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> SignalEventResponse:
    """Retrieve a canonical event by ID."""
    event = await event_repo.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found",
        )
    return SignalEventResponse(
        event_id=event.event_id,
        source_type=event.source_type,
        source_id=event.source_id,
        tenant_id=event.tenant_id,
        event_type=event.event_type,
        severity=event.severity.value,
        payload_hash=event.payload_hash,
        coalesce_key=event.coalesce_key,
        status=event.status.value,
        is_duplicate=False,
        metadata=event.metadata,
        created_at=event.created_at,
        deadline_at=event.deadline_at,
    )


_ingestion_paused: bool = False


def is_ingestion_paused() -> bool:
    """Return whether background signal ingestion is currently paused."""
    return _ingestion_paused


@router.post(
    "/api/v1/ingestion/pause",
    summary="Pause Background Signal Ingestion",
)
async def pause_ingestion() -> dict[str, Any]:
    """Pause background signal poller loop to prevent API calls."""
    global _ingestion_paused
    _ingestion_paused = True
    return {"status": "paused", "ingestion_paused": True}


@router.post(
    "/api/v1/ingestion/resume",
    summary="Resume Background Signal Ingestion",
)
async def resume_ingestion() -> dict[str, Any]:
    """Resume background signal poller loop."""
    global _ingestion_paused
    _ingestion_paused = False
    return {"status": "resumed", "ingestion_paused": False}


@router.get(
    "/api/v1/ingestion/status",
    summary="Get Ingestion Status",
)
async def get_ingestion_status() -> dict[str, Any]:
    """Get current background ingestion pause state."""
    return {"ingestion_paused": _ingestion_paused}
