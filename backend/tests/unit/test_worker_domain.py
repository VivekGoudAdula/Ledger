"""Unit Tests for Worker Domain Entities.

Validates execution checkpoint tracking, execution result schemas, and worker status telemetry.
"""

from datetime import datetime, timezone
import pytest

from app.domain.models import ExecutionCheckpoint, ExecutionResult, WorkerStatus


def test_valid_execution_checkpoint_accepted():
    chk = ExecutionCheckpoint(work_item_id="item_1", worker_id="worker-1", attempt_number=1)
    assert chk.work_item_id == "item_1"
    assert chk.worker_id == "worker-1"
    assert chk.state == "PROCESSING"


def test_invalid_attempt_number_rejected():
    with pytest.raises(ValueError, match="attempt_number"):
        ExecutionCheckpoint(work_item_id="item_1", worker_id="worker-1", attempt_number=0)


def test_valid_execution_result_accepted():
    res = ExecutionResult(
        execution_id="EXEC-001",
        work_item_id="item_1",
        status="COMPLETED",
        output_data={"action": "analyzed"},
    )
    assert res.execution_id == "EXEC-001"
    assert res.status == "COMPLETED"


def test_invalid_execution_status_rejected():
    with pytest.raises(ValueError, match="Invalid ExecutionResult status"):
        ExecutionResult(
            execution_id="EXEC-002",
            work_item_id="item_1",
            status="INVALID_STATUS",
        )
