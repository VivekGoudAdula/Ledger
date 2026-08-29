"""Dashboard API Routes & WebSocket Stream.

Provides GET /api/v1/dashboard/summary REST endpoint and /ws/dashboard WebSocket endpoint.
"""

import asyncio
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.dashboard.schemas import DashboardSummaryDTO
from app.dashboard.service import DashboardService
from app.api.dependencies import get_dashboard_service, _global_memory_broker
from app.storage.database import AsyncSessionLocal
from app.storage.repositories import EventRepository, ExecutionRepository, IdempotencyRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])
ws_router = APIRouter(tags=["WebSocket Dashboard"])


@router.get("/summary", response_model=DashboardSummaryDTO)
async def get_dashboard_summary(
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardSummaryDTO:
    """Retrieve full live operational dashboard summary snapshot."""
    return await dashboard_service.build_dashboard_summary()


@ws_router.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket) -> None:
    """Stream live dashboard summary updates over WebSocket every 1.0s with short-lived DB sessions."""
    await websocket.accept()
    logger.info("WebSocket Dashboard client connected: %s", websocket.client)
    try:
        while True:
            async with AsyncSessionLocal() as session:
                event_repo = EventRepository(session)
                exec_repo = ExecutionRepository(session)
                idem_repo = IdempotencyRepository(session)
                dashboard_service = DashboardService(
                    event_repo=event_repo,
                    execution_repo=exec_repo,
                    idempotency_repo=idem_repo,
                    broker=_global_memory_broker,
                )
                summary = await dashboard_service.build_dashboard_summary()
                await websocket.send_json(summary.model_dump())
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("WebSocket Dashboard client disconnected: %s", websocket.client)
    except Exception as err:
        logger.warning("WebSocket Dashboard error: %s", err)
        try:
            await websocket.close()
        except Exception:
            pass
