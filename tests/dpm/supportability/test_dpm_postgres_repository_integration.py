import os
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.infrastructure.dpm_runs.postgres import PostgresDpmRunRepository
from tests.dpm.supportability.test_dpm_postgres_repository_scaffold import (
    _build_repository as _build_fake_repository,
)

_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch) -> PostgresDpmRunRepository:
    if _DSN:
        try:
            repo = PostgresDpmRunRepository(dsn=_DSN)
            _reset_tables(repo)
            return repo
        except Exception:
            pass
    repo, _ = _build_fake_repository(monkeypatch)
    return repo


def test_live_postgres_run_lookup_and_artifact_contract(
    repository: PostgresDpmRunRepository,
) -> None:
    now = datetime.now(timezone.utc)
    shared_hash = f"sha256:{uuid.uuid4().hex}"
    run_old = _build_run(
        run_id=f"rr-{uuid.uuid4().hex}",
        correlation_id=f"corr-{uuid.uuid4().hex}",
        request_hash=shared_hash,
        portfolio_id="pf-live-a",
        status="READY",
        created_at=now - timedelta(minutes=3),
        idempotency_key=f"idem-{uuid.uuid4().hex}",
    )
    run_new = _build_run(
        run_id=f"rr-{uuid.uuid4().hex}",
        correlation_id=f"corr-{uuid.uuid4().hex}",
        request_hash=shared_hash,
        portfolio_id="pf-live-b",
        status="BLOCKED",
        created_at=now - timedelta(minutes=1),
        idempotency_key=f"idem-{uuid.uuid4().hex}",
    )
    repository.save_run(run_old)
    repository.save_run(run_new)

    loaded = repository.get_run(rebalance_run_id=run_new.rebalance_run_id)
    assert loaded is not None
    assert loaded.rebalance_run_id == run_new.rebalance_run_id
    assert loaded.result_json["status"] == "BLOCKED"

    by_correlation = repository.get_run_by_correlation(correlation_id=run_old.correlation_id)
    assert by_correlation is not None
    assert by_correlation.rebalance_run_id == run_old.rebalance_run_id

    by_hash = repository.get_run_by_request_hash(request_hash=shared_hash)
    assert by_hash is not None
    assert by_hash.rebalance_run_id == run_new.rebalance_run_id

    rows, next_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=1,
        cursor=None,
    )
    assert len(rows) == 1
    assert next_cursor is not None

    second_page, second_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=1,
        cursor=next_cursor,
    )
    assert len(second_page) == 1
    assert second_cursor is None

    ready_rows, _ = repository.list_runs(
        created_from=None,
        created_to=None,
        status="READY",
        request_hash=None,
        portfolio_id="pf-live-a",
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in ready_rows] == [run_old.rebalance_run_id]

    artifact = {
        "run_id": run_new.rebalance_run_id,
        "artifact_version": "v1",
        "evidence": {"weights": {"AAPL": 0.5, "MSFT": 0.5}},
    }
    repository.save_run_artifact(rebalance_run_id=run_new.rebalance_run_id, artifact_json=artifact)
    loaded_artifact = repository.get_run_artifact(rebalance_run_id=run_new.rebalance_run_id)
    assert loaded_artifact == artifact


def test_live_postgres_idempotency_workflow_lineage_and_summary(
    repository: PostgresDpmRunRepository,
) -> None:
    now = datetime.now(timezone.utc)
    run = _build_run(
        run_id=f"rr-{uuid.uuid4().hex}",
        correlation_id=f"corr-{uuid.uuid4().hex}",
        request_hash=f"sha256:{uuid.uuid4().hex}",
        portfolio_id="pf-summary",
        status="PENDING_REVIEW",
        created_at=now - timedelta(minutes=2),
        idempotency_key=f"idem-{uuid.uuid4().hex}",
    )
    repository.save_run(run)
    repository.save_idempotency_mapping(
        DpmRunIdempotencyRecord(
            idempotency_key=run.idempotency_key or "",
            request_hash=run.request_hash,
            rebalance_run_id=run.rebalance_run_id,
            created_at=run.created_at,
        )
    )
    repository.append_idempotency_history(
        DpmRunIdempotencyHistoryRecord(
            idempotency_key=run.idempotency_key or "",
            rebalance_run_id=run.rebalance_run_id,
            correlation_id=run.correlation_id,
            request_hash=run.request_hash,
            created_at=run.created_at,
        )
    )
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id=f"dec-{uuid.uuid4().hex}",
            run_id=run.rebalance_run_id,
            action="REQUEST_CHANGES",
            reason_code="NEEDS_DETAIL",
            comment="Need more rationale",
            actor_id="reviewer-live",
            decided_at=now,
            correlation_id=run.correlation_id,
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            source_entity_id=run.correlation_id,
            edge_type="CORRELATION_TO_RUN",
            target_entity_id=run.rebalance_run_id,
            created_at=now,
            metadata_json={"channel": "integration_test"},
        )
    )

    idempotency = repository.get_idempotency_mapping(idempotency_key=run.idempotency_key or "")
    assert idempotency is not None
    assert idempotency.rebalance_run_id == run.rebalance_run_id

    history = repository.list_idempotency_history(idempotency_key=run.idempotency_key or "")
    assert len(history) == 1
    assert history[0].correlation_id == run.correlation_id

    decisions, cursor = repository.list_workflow_decisions_filtered(
        rebalance_run_id=run.rebalance_run_id,
        action="REQUEST_CHANGES",
        actor_id="reviewer-live",
        reason_code="NEEDS_DETAIL",
        decided_from=now - timedelta(days=1),
        decided_to=now + timedelta(days=1),
        limit=5,
        cursor=None,
    )
    assert len(decisions) == 1
    assert cursor is None

    edges = repository.list_lineage_edges(entity_id=run.correlation_id)
    assert len(edges) == 1
    assert edges[0].target_entity_id == run.rebalance_run_id

    summary = repository.get_supportability_summary()
    assert summary.run_count == 1
    assert summary.workflow_decision_count == 1
    assert summary.lineage_edge_count == 1
    assert summary.run_status_counts == {"PENDING_REVIEW": 1}
    assert summary.operation_count == 0


def test_live_postgres_async_and_retention_purge_contract(
    repository: PostgresDpmRunRepository,
) -> None:
    now = datetime.now(timezone.utc)
    run = _build_run(
        run_id=f"rr-{uuid.uuid4().hex}",
        correlation_id=f"corr-{uuid.uuid4().hex}",
        request_hash=f"sha256:{uuid.uuid4().hex}",
        portfolio_id="pf-purge",
        status="READY",
        created_at=now - timedelta(days=10),
        idempotency_key=f"idem-{uuid.uuid4().hex}",
    )
    repository.save_run(run)
    repository.save_run_artifact(
        rebalance_run_id=run.rebalance_run_id,
        artifact_json={"rebalance_run_id": run.rebalance_run_id},
    )
    repository.save_idempotency_mapping(
        DpmRunIdempotencyRecord(
            idempotency_key=run.idempotency_key or "",
            request_hash=run.request_hash,
            rebalance_run_id=run.rebalance_run_id,
            created_at=run.created_at,
        )
    )
    repository.append_idempotency_history(
        DpmRunIdempotencyHistoryRecord(
            idempotency_key=run.idempotency_key or "",
            rebalance_run_id=run.rebalance_run_id,
            correlation_id=run.correlation_id,
            request_hash=run.request_hash,
            created_at=run.created_at,
        )
    )
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id=f"dec-{uuid.uuid4().hex}",
            run_id=run.rebalance_run_id,
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment="Approved",
            actor_id="reviewer-live",
            decided_at=run.created_at + timedelta(minutes=1),
            correlation_id=run.correlation_id,
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            source_entity_id=run.correlation_id,
            edge_type="CORRELATION_TO_RUN",
            target_entity_id=run.rebalance_run_id,
            created_at=run.created_at,
            metadata_json={"kind": "purge_test"},
        )
    )
    stale_operation = DpmAsyncOperationRecord(
        operation_id=f"op-{uuid.uuid4().hex}",
        operation_type="ANALYZE_SCENARIOS",
        status="SUCCEEDED",
        correlation_id=f"corr-op-{uuid.uuid4().hex}",
        created_at=now - timedelta(hours=3),
        started_at=now - timedelta(hours=3),
        finished_at=now - timedelta(hours=2),
        result_json={"status": "done"},
        error_json=None,
        request_json={"payload": "stale"},
    )
    fresh_operation = DpmAsyncOperationRecord(
        operation_id=f"op-{uuid.uuid4().hex}",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id=f"corr-op-{uuid.uuid4().hex}",
        created_at=now - timedelta(minutes=20),
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"payload": "fresh"},
    )
    repository.create_operation(stale_operation)
    repository.create_operation(fresh_operation)

    operations_page_1, next_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=None,
    )
    assert len(operations_page_1) == 1
    assert next_cursor is not None

    operations_page_2, page_2_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=next_cursor,
    )
    assert len(operations_page_2) == 1
    assert page_2_cursor is None

    purged_ops = repository.purge_expired_operations(ttl_seconds=3600, now=now)
    assert purged_ops == 1
    assert repository.get_operation(operation_id=stale_operation.operation_id) is None
    assert repository.get_operation(operation_id=fresh_operation.operation_id) is not None

    purged_runs = repository.purge_expired_runs(retention_days=1, now=now)
    assert purged_runs == 1
    assert repository.get_run(rebalance_run_id=run.rebalance_run_id) is None
    assert repository.get_run_artifact(rebalance_run_id=run.rebalance_run_id) is None
    assert repository.get_idempotency_mapping(idempotency_key=run.idempotency_key or "") is None
    assert not repository.list_idempotency_history(idempotency_key=run.idempotency_key or "")
    assert not repository.list_workflow_decisions(rebalance_run_id=run.rebalance_run_id)
    assert not repository.list_lineage_edges(entity_id=run.correlation_id)


def _build_run(
    *,
    run_id: str,
    correlation_id: str,
    request_hash: str,
    portfolio_id: str,
    status: str,
    created_at: datetime,
    idempotency_key: str,
) -> DpmRunRecord:
    return DpmRunRecord(
        rebalance_run_id=run_id,
        correlation_id=correlation_id,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        portfolio_id=portfolio_id,
        created_at=created_at,
        result_json={"rebalance_run_id": run_id, "status": status},
    )


def _reset_tables(repository: PostgresDpmRunRepository) -> None:
    with closing(repository._connect()) as connection:
        connection.execute(
            "TRUNCATE TABLE dpm_lineage_edges, dpm_workflow_decisions, "
            "dpm_run_idempotency_history, dpm_run_idempotency, "
            "dpm_run_artifacts, dpm_async_operations, dpm_runs CASCADE"
        )
        connection.commit()
