"""API routes package exports."""

from app.api.routes.signals import router as signals_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.valuation import router as valuation_router
from app.api.routes.admission import router as admission_router
from app.api.routes.queue import router as queue_router
from app.api.routes.dashboard import router as dashboard_router, ws_router as ws_dashboard_router
from app.api.routes.benchmark import router as benchmark_router
from app.api.routes.admin import router as admin_router

__all__ = [
    "signals_router",
    "incidents_router",
    "valuation_router",
    "admission_router",
    "queue_router",
    "dashboard_router",
    "ws_dashboard_router",
    "benchmark_router",
    "admin_router",
]
