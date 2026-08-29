"""Integration tests for Worker Fault Injection REST API Endpoints."""

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Provide TestClient instance."""
    return TestClient(app)


def test_fault_injection_api_disabled_by_default(client, monkeypatch):
    """Verify that admin endpoints return 403 when LEDGER_FAULT_INJECTION_ENABLED is false."""
    monkeypatch.setattr(settings, "LEDGER_FAULT_INJECTION_ENABLED", False)

    response = client.get("/api/v1/admin/workers")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]

    pause_resp = client.post("/api/v1/admin/workers/worker-1/pause")
    assert pause_resp.status_code == 403


def test_fault_injection_api_enabled_workflow(client, monkeypatch):
    """Verify worker pause, resume, inject failure, clear failure endpoints when enabled."""
    monkeypatch.setattr(settings, "LEDGER_FAULT_INJECTION_ENABLED", True)

    # 1. List Workers State
    resp = client.get("/api/v1/admin/workers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fault_injection_enabled"] is True
    assert len(data["workers"]) >= 3

    # 2. Pause Worker-1
    pause_resp = client.post("/api/v1/admin/workers/worker-1/pause")
    assert pause_resp.status_code == 200
    w1_data = pause_resp.json()
    assert w1_data["worker_id"] == "worker-1"
    assert w1_data["state"] == "PAUSED"
    assert w1_data["is_paused"] is True

    # 3. Resume Worker-1
    resume_resp = client.post("/api/v1/admin/workers/worker-1/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["state"] == "RUNNING"

    # 4. Inject Failure into Worker-2
    inject_resp = client.post(
        "/api/v1/admin/workers/worker-2/inject-failure",
        json={"failure_mode": "after_execution_before_ack", "one_shot": True},
    )
    assert inject_resp.status_code == 200
    w2_data = inject_resp.json()
    assert w2_data["worker_id"] == "worker-2"
    assert w2_data["active_failure_mode"] == "after_execution_before_ack"

    # 5. Clear Failure for Worker-2
    clear_resp = client.post("/api/v1/admin/workers/worker-2/clear-failure")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["active_failure_mode"] is None


def test_fault_injection_api_unknown_worker_returns_404(client, monkeypatch):
    """Verify unknown worker ID returns 404 Not Found."""
    monkeypatch.setattr(settings, "LEDGER_FAULT_INJECTION_ENABLED", True)

    resp = client.post("/api/v1/admin/workers/non_existent_worker_xyz/pause")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_fault_injection_api_invalid_failure_mode_returns_422(client, monkeypatch):
    """Verify invalid failure mode name returns 422 Unprocessable Entity."""
    monkeypatch.setattr(settings, "LEDGER_FAULT_INJECTION_ENABLED", True)

    resp = client.post(
        "/api/v1/admin/workers/worker-1/inject-failure",
        json={"failure_mode": "invalid_mode_name", "one_shot": True},
    )
    assert resp.status_code == 422
