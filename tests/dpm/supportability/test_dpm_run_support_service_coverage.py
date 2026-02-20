import pytest

from src.core.dpm_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository


def _build_service(*, workflow_enabled: bool = False) -> DpmRunSupportService:
    return DpmRunSupportService(
        repository=InMemoryDpmRunRepository(),
        workflow_enabled=workflow_enabled,
    )


def test_service_operation_state_mutation_and_missing_operation_errors():
    service = _build_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-service-op-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    service.mark_operation_running(operation_id=accepted.operation_id)
    running = service.get_async_operation(operation_id=accepted.operation_id)
    assert running.status == "RUNNING"
    assert running.started_at is not None

    service.complete_operation_success(operation_id=accepted.operation_id, result_json={"ok": True})
    succeeded = service.get_async_operation(operation_id=accepted.operation_id)
    assert succeeded.status == "SUCCEEDED"
    assert succeeded.result == {"ok": True}
    assert succeeded.error is None

    accepted_failed = service.submit_analyze_async(
        correlation_id="corr-service-op-2",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    service.complete_operation_failure(
        operation_id=accepted_failed.operation_id,
        code="FAILED_TEST",
        message="failed",
    )
    failed = service.get_async_operation(operation_id=accepted_failed.operation_id)
    assert failed.status == "FAILED"
    assert failed.result is None
    assert failed.error is not None
    assert failed.error.code == "FAILED_TEST"
    assert failed.error.message == "failed"

    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.mark_operation_running(operation_id="dop_missing")
    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.complete_operation_success(operation_id="dop_missing", result_json={"ok": True})
    with pytest.raises(DpmRunNotFoundError, match="DPM_ASYNC_OPERATION_NOT_FOUND"):
        service.complete_operation_failure(
            operation_id="dop_missing",
            code="ERR",
            message="missing",
        )


def test_service_apply_workflow_action_missing_run():
    service = _build_service(workflow_enabled=True)
    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.apply_workflow_action(
            rebalance_run_id="rr_missing",
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="reviewer_1",
            correlation_id="corr-workflow-missing",
        )
