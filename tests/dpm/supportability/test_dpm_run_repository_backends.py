from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository, SqliteDpmRunRepository


@pytest.fixture(params=["IN_MEMORY", "SQLITE"])
def repository(request):
    if request.param == "IN_MEMORY":
        yield InMemoryDpmRunRepository()
        return
    with TemporaryDirectory() as tmp_dir:
        sqlite_path = str(Path(tmp_dir) / "supportability.sqlite")
        yield SqliteDpmRunRepository(database_path=sqlite_path)


def test_repository_run_and_idempotency_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run = DpmRunRecord(
        rebalance_run_id="rr_repo_1",
        correlation_id="corr_repo_1",
        request_hash="sha256:req1",
        idempotency_key="idem_repo_1",
        portfolio_id="pf_repo_1",
        created_at=now,
        result_json={"rebalance_run_id": "rr_repo_1", "status": "READY"},
    )
    repository.save_run(run)

    stored_run = repository.get_run(rebalance_run_id="rr_repo_1")
    assert stored_run is not None
    assert stored_run.rebalance_run_id == "rr_repo_1"
    assert stored_run.correlation_id == "corr_repo_1"
    assert stored_run.result_json["status"] == "READY"

    by_correlation = repository.get_run_by_correlation(correlation_id="corr_repo_1")
    assert by_correlation is not None
    assert by_correlation.rebalance_run_id == "rr_repo_1"

    record = DpmRunIdempotencyRecord(
        idempotency_key="idem_repo_1",
        request_hash="sha256:req1",
        rebalance_run_id="rr_repo_1",
        created_at=now,
    )
    repository.save_idempotency_mapping(record)
    stored_idem = repository.get_idempotency_mapping(idempotency_key="idem_repo_1")
    assert stored_idem is not None
    assert stored_idem.rebalance_run_id == "rr_repo_1"


def test_repository_async_operations_and_ttl_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    operation = DpmAsyncOperationRecord(
        operation_id="dop_repo_1",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="corr_op_1",
        created_at=now,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    repository.create_operation(operation)
    stored = repository.get_operation(operation_id="dop_repo_1")
    assert stored is not None
    assert stored.status == "PENDING"

    operation.status = "SUCCEEDED"
    operation.started_at = now + timedelta(seconds=1)
    operation.finished_at = now + timedelta(seconds=2)
    operation.result_json = {"ok": True}
    operation.request_json = None
    repository.update_operation(operation)

    updated = repository.get_operation_by_correlation(correlation_id="corr_op_1")
    assert updated is not None
    assert updated.status == "SUCCEEDED"
    assert updated.result_json == {"ok": True}
    assert updated.request_json is None

    removed = repository.purge_expired_operations(
        ttl_seconds=1,
        now=now + timedelta(seconds=10),
    )
    assert removed == 1
    assert repository.get_operation(operation_id="dop_repo_1") is None


def test_repository_workflow_decision_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    decision_one = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_repo_1",
        run_id="rr_repo_1",
        action="REQUEST_CHANGES",
        reason_code="NEEDS_DETAIL",
        comment="Add details",
        actor_id="ops_1",
        decided_at=now,
        correlation_id="corr_wf_1",
    )
    decision_two = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_repo_2",
        run_id="rr_repo_1",
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="ops_2",
        decided_at=now + timedelta(seconds=1),
        correlation_id="corr_wf_2",
    )
    repository.append_workflow_decision(decision_one)
    repository.append_workflow_decision(decision_two)

    decisions = repository.list_workflow_decisions(rebalance_run_id="rr_repo_1")
    assert [decision.decision_id for decision in decisions] == ["dwd_repo_1", "dwd_repo_2"]
    assert decisions[0].action == "REQUEST_CHANGES"
    assert decisions[1].action == "APPROVE"
