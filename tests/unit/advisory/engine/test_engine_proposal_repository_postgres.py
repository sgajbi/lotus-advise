import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType

import src.infrastructure.proposals.postgres as postgres_module
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalSimulationIdempotencyRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.proposals.postgres import PostgresProposalRepository


class _FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self):
        self.idempotency = {}
        self.simulation_idempotency = {}
        self.operations = {}
        self.proposals = {}
        self.versions = {}
        self.events = {}
        self.approvals = {}
        self.schema_migrations = {}

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if sql == "SELECT pg_advisory_lock(%s::bigint)":
            return _FakeCursor()
        if sql == "SELECT pg_advisory_unlock(%s::bigint)":
            return _FakeCursor()
        if sql.startswith("CREATE TABLE"):
            return _FakeCursor()
        if sql.startswith("ALTER TABLE proposal_records ADD COLUMN IF NOT EXISTS lifecycle_origin"):
            for row in self.proposals.values():
                row.setdefault("lifecycle_origin", "DIRECT_CREATE")
            return _FakeCursor()
        if sql.startswith(
            "ALTER TABLE proposal_records ADD COLUMN IF NOT EXISTS source_workspace_id"
        ):
            for row in self.proposals.values():
                row.setdefault("source_workspace_id", None)
            return _FakeCursor()
        if sql.startswith(
            "ALTER TABLE proposal_async_operations ADD COLUMN IF NOT EXISTS payload_json"
        ):
            for row in self.operations.values():
                row.setdefault("payload_json", "{}")
            return _FakeCursor()
        if sql.startswith(
            "ALTER TABLE proposal_async_operations ADD COLUMN IF NOT EXISTS attempt_count"
        ):
            for row in self.operations.values():
                row.setdefault("attempt_count", 0)
            return _FakeCursor()
        if sql.startswith(
            "ALTER TABLE proposal_async_operations ADD COLUMN IF NOT EXISTS max_attempts"
        ):
            for row in self.operations.values():
                row.setdefault("max_attempts", 3)
            return _FakeCursor()
        if sql.startswith(
            "ALTER TABLE proposal_async_operations ADD COLUMN IF NOT EXISTS lease_expires_at"
        ):
            for row in self.operations.values():
                row.setdefault("lease_expires_at", None)
            return _FakeCursor()
        if sql.startswith("CREATE INDEX") or sql.startswith("CREATE UNIQUE INDEX"):
            return _FakeCursor()
        if "FROM schema_migrations" in sql:
            namespace = args[0]
            rows = [
                {"version": version, "checksum": checksum}
                for (stored_namespace, version), checksum in self.schema_migrations.items()
                if stored_namespace == namespace
            ]
            rows = sorted(rows, key=lambda row: row["version"])
            return _FakeCursor(rows=rows)
        if "INSERT INTO schema_migrations" in sql:
            self.schema_migrations[(args[1], args[0])] = args[2]
            return _FakeCursor()
        if "INSERT INTO proposal_idempotency" in sql:
            self.idempotency[args[0]] = {
                "idempotency_key": args[0],
                "request_hash": args[1],
                "proposal_id": args[2],
                "proposal_version_no": args[3],
                "created_at": args[4],
            }
            return _FakeCursor()
        if "FROM proposal_idempotency WHERE idempotency_key = %s" in sql:
            return _FakeCursor(self.idempotency.get(args[0]))
        if "INSERT INTO proposal_simulation_idempotency" in sql:
            self.simulation_idempotency[args[0]] = {
                "idempotency_key": args[0],
                "request_hash": args[1],
                "response_json": args[2],
                "created_at": args[3],
            }
            return _FakeCursor()
        if "FROM proposal_simulation_idempotency WHERE idempotency_key = %s" in sql:
            return _FakeCursor(self.simulation_idempotency.get(args[0]))
        if "INSERT INTO proposal_async_operations" in sql:
            if (
                "ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING"
                in sql
            ):
                inserted_operation_id = args[0]
                idempotency_key = args[4]
                existing = next(
                    (
                        operation
                        for operation in self.operations.values()
                        if operation["idempotency_key"] == idempotency_key
                    ),
                    None,
                )
                if existing is None:
                    self.operations[inserted_operation_id] = {
                        "operation_id": args[0],
                        "operation_type": args[1],
                        "status": args[2],
                        "correlation_id": args[3],
                        "idempotency_key": args[4],
                        "proposal_id": args[5],
                        "created_by": args[6],
                        "created_at": args[7],
                        "payload_json": args[8],
                        "attempt_count": args[9],
                        "max_attempts": args[10],
                        "started_at": args[11],
                        "lease_expires_at": args[12],
                        "finished_at": args[13],
                        "result_json": args[14],
                        "error_json": args[15],
                    }
                    return _FakeCursor(self.operations[inserted_operation_id])
                return _FakeCursor(existing)
            self.operations[args[0]] = {
                "operation_id": args[0],
                "operation_type": args[1],
                "status": args[2],
                "correlation_id": args[3],
                "idempotency_key": args[4],
                "proposal_id": args[5],
                "created_by": args[6],
                "created_at": args[7],
                "payload_json": args[8],
                "attempt_count": args[9],
                "max_attempts": args[10],
                "started_at": args[11],
                "lease_expires_at": args[12],
                "finished_at": args[13],
                "result_json": args[14],
                "error_json": args[15],
            }
            return _FakeCursor()
        if "FROM proposal_async_operations WHERE operation_id = %s" in sql:
            return _FakeCursor(self.operations.get(args[0]))
        if "FROM proposal_async_operations WHERE correlation_id = %s" in sql:
            row = next(
                (
                    operation
                    for operation in self.operations.values()
                    if operation["correlation_id"] == args[0]
                ),
                None,
            )
            return _FakeCursor(row)
        if (
            "FROM proposal_async_operations WHERE idempotency_key = %s" in sql
            and "ORDER BY created_at DESC, operation_id DESC" in sql
        ):
            rows = [
                operation
                for operation in self.operations.values()
                if operation["idempotency_key"] == args[0]
            ]
            rows = sorted(
                rows,
                key=lambda row: (row["created_at"], row["operation_id"]),
                reverse=True,
            )
            return _FakeCursor(rows[0] if rows else None)
        if (
            "FROM proposal_async_operations" in sql
            and "ORDER BY created_at ASC, operation_id ASC" in sql
        ):
            as_of = args[0]
            rows = []
            for row in self.operations.values():
                if row["status"] == "PENDING":
                    rows.append(row)
                    continue
                if (
                    row["status"] == "RUNNING"
                    and row["finished_at"] is None
                    and row["lease_expires_at"] is not None
                    and row["lease_expires_at"] <= as_of
                ):
                    rows.append(row)
            rows = sorted(rows, key=lambda row: (row["created_at"], row["operation_id"]))
            return _FakeCursor(rows=rows)
        if "INSERT INTO proposal_records" in sql:
            self.proposals[args[0]] = {
                "proposal_id": args[0],
                "portfolio_id": args[1],
                "mandate_id": args[2],
                "jurisdiction": args[3],
                "created_by": args[4],
                "created_at": args[5],
                "last_event_at": args[6],
                "current_state": args[7],
                "current_version_no": args[8],
                "title": args[9],
                "advisor_notes": args[10],
                "lifecycle_origin": args[11],
                "source_workspace_id": args[12],
            }
            return _FakeCursor()
        if "FROM proposal_records WHERE proposal_id = %s" in sql:
            return _FakeCursor(self.proposals.get(args[0]))
        if "FROM proposal_records" in sql and "ORDER BY created_at DESC, proposal_id DESC" in sql:
            rows = list(self.proposals.values())
            arg_index = 0
            if "portfolio_id = %s" in sql:
                portfolio_id = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["portfolio_id"] == portfolio_id]
            if "current_state = %s" in sql:
                state = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["current_state"] == state]
            if "created_by = %s" in sql:
                created_by = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_by"] == created_by]
            if "created_at >= %s" in sql:
                created_from = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] >= created_from]
            if "created_at <= %s" in sql:
                created_to = args[arg_index]
                rows = [row for row in rows if row["created_at"] <= created_to]
            rows = sorted(
                rows,
                key=lambda row: (row["created_at"], row["proposal_id"]),
                reverse=True,
            )
            return _FakeCursor(rows=rows)
        if "INSERT INTO proposal_versions" in sql:
            self.versions[(args[1], args[2])] = {
                "proposal_version_id": args[0],
                "proposal_id": args[1],
                "version_no": args[2],
                "created_at": args[3],
                "request_hash": args[4],
                "artifact_hash": args[5],
                "simulation_hash": args[6],
                "status_at_creation": args[7],
                "proposal_result_json": args[8],
                "artifact_json": args[9],
                "evidence_bundle_json": args[10],
                "gate_decision_json": args[11],
            }
            return _FakeCursor()
        if "FROM proposal_versions WHERE proposal_id = %s AND version_no = %s" in sql:
            return _FakeCursor(self.versions.get((args[0], args[1])))
        if "FROM proposal_versions" in sql and "ORDER BY version_no DESC" in sql:
            proposal_id = args[0]
            rows = [row for (pid, _), row in self.versions.items() if pid == proposal_id]
            rows = sorted(rows, key=lambda row: row["version_no"], reverse=True)
            return _FakeCursor(rows[0] if rows else None)
        if "INSERT INTO proposal_workflow_events" in sql:
            self.events[args[0]] = {
                "event_id": args[0],
                "proposal_id": args[1],
                "event_type": args[2],
                "from_state": args[3],
                "to_state": args[4],
                "actor_id": args[5],
                "occurred_at": args[6],
                "reason_json": args[7],
                "related_version_no": args[8],
            }
            return _FakeCursor()
        if (
            "FROM proposal_workflow_events" in sql
            and "ORDER BY occurred_at ASC, event_id ASC" in sql
        ):
            rows = [row for row in self.events.values() if row["proposal_id"] == args[0]]
            rows = sorted(rows, key=lambda row: (row["occurred_at"], row["event_id"]))
            return _FakeCursor(rows=rows)
        if "INSERT INTO proposal_approvals" in sql:
            self.approvals[args[0]] = {
                "approval_id": args[0],
                "proposal_id": args[1],
                "approval_type": args[2],
                "approved": args[3],
                "actor_id": args[4],
                "occurred_at": args[5],
                "details_json": args[6],
                "related_version_no": args[7],
            }
            return _FakeCursor()
        if "FROM proposal_approvals" in sql and "ORDER BY occurred_at ASC, approval_id ASC" in sql:
            rows = [row for row in self.approvals.values() if row["proposal_id"] == args[0]]
            rows = sorted(rows, key=lambda row: (row["occurred_at"], row["approval_id"]))
            return _FakeCursor(rows=rows)
        raise AssertionError(f"Unhandled SQL in fake connection: {sql}")

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def _build_repository(monkeypatch):
    connection = _FakeConnection()
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: object())
    monkeypatch.setattr(
        PostgresProposalRepository,
        "_connect",
        lambda self: connection,  # noqa: ARG005
    )
    repository = PostgresProposalRepository(dsn="postgresql://user:pass@localhost:5432/proposals")
    return repository, connection


def test_postgres_repository_requires_dsn():
    try:
        PostgresProposalRepository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing proposal postgres dsn")


def test_postgres_repository_requires_driver(monkeypatch):
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: None)
    try:
        PostgresProposalRepository(dsn="postgresql://user:pass@localhost:5432/proposals")
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError for missing proposal postgres driver")


def test_postgres_repository_idempotency_roundtrip(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    created_at = datetime.now(timezone.utc)
    record = ProposalIdempotencyRecord(
        idempotency_key="idem-prop-pg-1",
        request_hash="sha256:req",
        proposal_id="pp_001",
        proposal_version_no=1,
        created_at=created_at,
    )

    assert repository.get_idempotency(idempotency_key=record.idempotency_key) is None
    repository.save_idempotency(record)
    loaded = repository.get_idempotency(idempotency_key=record.idempotency_key)
    assert loaded is not None
    assert loaded.idempotency_key == "idem-prop-pg-1"
    assert loaded.request_hash == "sha256:req"
    assert loaded.proposal_id == "pp_001"
    assert loaded.proposal_version_no == 1
    assert loaded.created_at == created_at


def test_postgres_repository_simulation_idempotency_roundtrip(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    created_at = datetime.now(timezone.utc)
    record = ProposalSimulationIdempotencyRecord(
        idempotency_key="idem-prop-sim-pg-1",
        request_hash="sha256:req-sim",
        response_json={"proposal_run_id": "pr_001", "status": "READY"},
        created_at=created_at,
    )

    assert repository.get_simulation_idempotency(idempotency_key=record.idempotency_key) is None
    repository.save_simulation_idempotency(record)
    loaded = repository.get_simulation_idempotency(idempotency_key=record.idempotency_key)
    assert loaded is not None
    assert loaded.idempotency_key == record.idempotency_key
    assert loaded.request_hash == "sha256:req-sim"
    assert loaded.response_json["proposal_run_id"] == "pr_001"
    assert loaded.created_at == created_at


def test_postgres_repository_create_update_and_lookup_operation(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    created_at = datetime.now(timezone.utc)
    operation = ProposalAsyncOperationRecord(
        operation_id="pop_001",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr-prop-1",
        idempotency_key="idem-prop-pg-1",
        proposal_id=None,
        created_by="advisor_1",
        created_at=created_at,
        payload_json={"payload": {"created_by": "advisor_1"}, "idempotency_key": "idem-prop-pg-1"},
        attempt_count=0,
        max_attempts=3,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    repository.create_operation(operation)

    loaded = repository.get_operation(operation_id="pop_001")
    assert loaded is not None
    assert loaded.status == "PENDING"
    assert loaded.payload_json["idempotency_key"] == "idem-prop-pg-1"
    assert loaded.attempt_count == 0
    assert loaded.max_attempts == 3
    assert loaded.result_json is None
    assert loaded.error_json is None

    operation.status = "SUCCEEDED"
    operation.proposal_id = "pp_001"
    operation.attempt_count = 2
    operation.started_at = created_at
    operation.lease_expires_at = created_at
    operation.finished_at = created_at
    operation.result_json = {"proposal": {"proposal_id": "pp_001"}}
    operation.error_json = None
    repository.update_operation(operation)

    by_operation = repository.get_operation(operation_id="pop_001")
    assert by_operation is not None
    assert by_operation.status == "SUCCEEDED"
    assert by_operation.proposal_id == "pp_001"
    assert by_operation.attempt_count == 2
    assert by_operation.lease_expires_at == created_at
    assert by_operation.result_json == {"proposal": {"proposal_id": "pp_001"}}
    assert by_operation.error_json is None
    assert by_operation.started_at == created_at
    assert by_operation.finished_at == created_at

    by_correlation = repository.get_operation_by_correlation(correlation_id="corr-prop-1")
    assert by_correlation is not None
    assert by_correlation.operation_id == "pop_001"
    assert by_correlation.status == "SUCCEEDED"


def test_postgres_repository_create_operation_if_absent_by_idempotency_is_atomic(monkeypatch):
    repository, connection = _build_repository(monkeypatch)
    created_at = datetime.now(timezone.utc)
    first = ProposalAsyncOperationRecord(
        operation_id="pop_atomic_1",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr-atomic-1",
        idempotency_key="idem-atomic-1",
        proposal_id=None,
        created_by="advisor_1",
        created_at=created_at,
        payload_json={"payload": {"created_by": "advisor_1"}, "submission_hash": "sha256:first"},
        attempt_count=0,
        max_attempts=3,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    second = ProposalAsyncOperationRecord(
        operation_id="pop_atomic_2",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr-atomic-2",
        idempotency_key="idem-atomic-1",
        proposal_id=None,
        created_by="advisor_2",
        created_at=created_at,
        payload_json={"payload": {"created_by": "advisor_2"}, "submission_hash": "sha256:second"},
        attempt_count=0,
        max_attempts=3,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )

    stored_first, first_is_new = repository.create_operation_if_absent_by_idempotency(first)
    stored_second, second_is_new = repository.create_operation_if_absent_by_idempotency(second)
    by_idempotency = repository.get_operation_by_idempotency(idempotency_key="idem-atomic-1")

    assert first_is_new is True
    assert second_is_new is False
    assert stored_first.operation_id == "pop_atomic_1"
    assert stored_second.operation_id == "pop_atomic_1"
    assert by_idempotency is not None
    assert by_idempotency.operation_id == "pop_atomic_1"
    assert by_idempotency.correlation_id == "corr-atomic-1"
    assert list(connection.operations) == ["pop_atomic_1"]


def test_postgres_repository_lists_recoverable_operations(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime.now(timezone.utc)
    pending = ProposalAsyncOperationRecord(
        operation_id="pop_pending",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr-pending",
        idempotency_key="idem-pending",
        proposal_id=None,
        created_by="advisor_1",
        created_at=now,
        payload_json={"payload": {"created_by": "advisor_1"}, "idempotency_key": "idem-pending"},
        attempt_count=0,
        max_attempts=3,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    expired_running = ProposalAsyncOperationRecord(
        operation_id="pop_expired",
        operation_type="CREATE_PROPOSAL_VERSION",
        status="RUNNING",
        correlation_id="corr-expired",
        idempotency_key=None,
        proposal_id="pp_001",
        created_by="advisor_1",
        created_at=now,
        payload_json={"proposal_id": "pp_001", "payload": {"created_by": "advisor_1"}},
        attempt_count=1,
        max_attempts=3,
        started_at=now,
        lease_expires_at=now,
        finished_at=None,
        result_json=None,
        error_json={"code": "RuntimeError", "message": "timeout"},
    )
    running = ProposalAsyncOperationRecord(
        operation_id="pop_running",
        operation_type="CREATE_PROPOSAL",
        status="RUNNING",
        correlation_id="corr-running",
        idempotency_key="idem-running",
        proposal_id=None,
        created_by="advisor_1",
        created_at=now,
        payload_json={"payload": {"created_by": "advisor_1"}, "idempotency_key": "idem-running"},
        attempt_count=1,
        max_attempts=3,
        started_at=now,
        lease_expires_at=now + timedelta(minutes=5),
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    succeeded = ProposalAsyncOperationRecord(
        operation_id="pop_succeeded",
        operation_type="CREATE_PROPOSAL",
        status="SUCCEEDED",
        correlation_id="corr-succeeded",
        idempotency_key="idem-succeeded",
        proposal_id="pp_002",
        created_by="advisor_1",
        created_at=now,
        payload_json={"payload": {"created_by": "advisor_1"}, "idempotency_key": "idem-succeeded"},
        attempt_count=1,
        max_attempts=3,
        started_at=now,
        lease_expires_at=None,
        finished_at=now,
        result_json={"proposal": {"proposal_id": "pp_002"}},
        error_json=None,
    )
    for operation in [pending, expired_running, running, succeeded]:
        repository.create_operation(operation)

    recoverable = repository.list_recoverable_operations(as_of=now)

    assert [operation.operation_id for operation in recoverable] == ["pop_expired", "pop_pending"]


def test_postgres_repository_proposal_create_update_get_and_list(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    first_created = datetime.now(timezone.utc)
    first = ProposalRecord(
        proposal_id="pp_a",
        portfolio_id="pf_repo",
        mandate_id="mandate_1",
        jurisdiction="SG",
        created_by="advisor_a",
        created_at=first_created,
        last_event_at=first_created,
        current_state="DRAFT",
        current_version_no=1,
        title="A",
        advisor_notes="note-a",
    )
    repository.create_proposal(first)

    second_created = datetime.now(timezone.utc)
    second = ProposalRecord(
        proposal_id="pp_b",
        portfolio_id="pf_repo",
        mandate_id="mandate_2",
        jurisdiction="SG",
        created_by="advisor_b",
        created_at=second_created,
        last_event_at=second_created,
        current_state="EXECUTION_READY",
        current_version_no=2,
        title="B",
        advisor_notes=None,
        lifecycle_origin="WORKSPACE_HANDOFF",
        source_workspace_id="aws_002",
    )
    repository.create_proposal(second)

    loaded_first = repository.get_proposal(proposal_id="pp_a")
    assert loaded_first is not None
    assert loaded_first.title == "A"
    assert loaded_first.current_state == "DRAFT"

    first.current_state = "CANCELLED"
    repository.update_proposal(first)
    updated_first = repository.get_proposal(proposal_id="pp_a")
    assert updated_first is not None
    assert updated_first.current_state == "CANCELLED"

    rows, next_cursor = repository.list_proposals(
        portfolio_id="pf_repo",
        state="EXECUTION_READY",
        created_by="advisor_b",
        created_from=None,
        created_to=None,
        limit=1,
        cursor=None,
    )
    assert len(rows) == 1
    assert rows[0].proposal_id == "pp_b"
    assert rows[0].lifecycle_origin == "WORKSPACE_HANDOFF"
    assert rows[0].source_workspace_id == "aws_002"
    assert next_cursor is None

    rows, _ = repository.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=1,
        cursor="pp_b",
    )
    assert len(rows) == 1
    assert rows[0].proposal_id == "pp_a"

    rows, next_cursor = repository.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=1,
        cursor="pp_missing",
    )
    assert rows == []
    assert next_cursor is None


def test_postgres_repository_version_create_get_and_current(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime.now(timezone.utc)
    version_1 = ProposalVersionRecord(
        proposal_version_id="ppv_001",
        proposal_id="pp_001",
        version_no=1,
        created_at=now,
        request_hash="sha256:req1",
        artifact_hash="sha256:artifact1",
        simulation_hash="sha256:sim1",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={"artifact_id": "a1"},
        evidence_bundle_json={"hashes": {"artifact_hash": "sha256:artifact1"}},
        gate_decision_json=None,
    )
    version_2 = ProposalVersionRecord(
        proposal_version_id="ppv_002",
        proposal_id="pp_001",
        version_no=2,
        created_at=now,
        request_hash="sha256:req2",
        artifact_hash="sha256:artifact2",
        simulation_hash="sha256:sim2",
        status_at_creation="BLOCKED",
        proposal_result_json={"status": "BLOCKED"},
        artifact_json={"artifact_id": "a2"},
        evidence_bundle_json={"hashes": {"artifact_hash": "sha256:artifact2"}},
        gate_decision_json={"gate": "CLIENT_CONSENT_REQUIRED"},
    )
    repository.create_version(version_1)
    repository.create_version(version_2)

    loaded_1 = repository.get_version(proposal_id="pp_001", version_no=1)
    assert loaded_1 is not None
    assert loaded_1.proposal_version_id == "ppv_001"
    assert loaded_1.proposal_result_json == {"status": "READY"}
    assert loaded_1.gate_decision_json is None

    loaded_2 = repository.get_version(proposal_id="pp_001", version_no=2)
    assert loaded_2 is not None
    assert loaded_2.proposal_version_id == "ppv_002"
    assert loaded_2.gate_decision_json == {"gate": "CLIENT_CONSENT_REQUIRED"}

    missing = repository.get_version(proposal_id="pp_001", version_no=3)
    assert missing is None

    current = repository.get_current_version(proposal_id="pp_001")
    assert current is not None
    assert current.version_no == 2
    assert current.proposal_version_id == "ppv_002"

    empty_current = repository.get_current_version(proposal_id="pp_missing")
    assert empty_current is None


def test_postgres_repository_workflow_events_and_approvals_roundtrip(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    first_at = datetime.now(timezone.utc)
    second_at = datetime.now(timezone.utc)

    first_event = ProposalWorkflowEventRecord(
        event_id="pwe_001",
        proposal_id="pp_001",
        event_type="CREATED",
        from_state=None,
        to_state="DRAFT",
        actor_id="advisor_1",
        occurred_at=first_at,
        reason_json={"comment": "created"},
        related_version_no=1,
    )
    second_event = ProposalWorkflowEventRecord(
        event_id="pwe_002",
        proposal_id="pp_001",
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_1",
        occurred_at=second_at,
        reason_json={"comment": "submit"},
        related_version_no=1,
    )
    repository.append_event(first_event)
    repository.append_event(second_event)

    events = repository.list_events(proposal_id="pp_001")
    assert [event.event_id for event in events] == ["pwe_001", "pwe_002"]
    assert events[1].to_state == "RISK_REVIEW"
    assert events[1].reason_json == {"comment": "submit"}

    approval_at = datetime.now(timezone.utc)
    approval = ProposalApprovalRecordData(
        approval_id="pap_001",
        proposal_id="pp_001",
        approval_type="RISK",
        approved=True,
        actor_id="risk_officer_1",
        occurred_at=approval_at,
        details_json={"ticket_id": "risk-42"},
        related_version_no=1,
    )
    repository.create_approval(approval)
    approvals = repository.list_approvals(proposal_id="pp_001")
    assert len(approvals) == 1
    assert approvals[0].approval_id == "pap_001"
    assert approvals[0].details_json == {"ticket_id": "risk-42"}


def test_postgres_repository_transition_proposal_writes_all_records(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime.now(timezone.utc)
    proposal = ProposalRecord(
        proposal_id="pp_002",
        portfolio_id="pf_repo",
        mandate_id="mandate_1",
        jurisdiction="SG",
        created_by="advisor_a",
        created_at=now,
        last_event_at=now,
        current_state="RISK_REVIEW",
        current_version_no=1,
        title="Needs Risk Signoff",
        advisor_notes="priority",
    )
    event = ProposalWorkflowEventRecord(
        event_id="pwe_010",
        proposal_id="pp_002",
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_a",
        occurred_at=now,
        reason_json={"comment": "submitted"},
        related_version_no=1,
    )
    approval = ProposalApprovalRecordData(
        approval_id="pap_010",
        proposal_id="pp_002",
        approval_type="RISK",
        approved=True,
        actor_id="risk_1",
        occurred_at=now,
        details_json={"ticket_id": "risk-010"},
        related_version_no=1,
    )

    result = repository.transition_proposal(proposal=proposal, event=event, approval=approval)
    assert result.proposal.proposal_id == "pp_002"
    assert result.event.event_id == "pwe_010"
    assert result.approval is not None
    assert result.approval.approval_id == "pap_010"

    stored_proposal = repository.get_proposal(proposal_id="pp_002")
    assert stored_proposal is not None
    assert stored_proposal.current_state == "RISK_REVIEW"
    stored_event_ids = [
        stored_event.event_id for stored_event in repository.list_events(proposal_id="pp_002")
    ]
    assert stored_event_ids == ["pwe_010"]
    assert [
        stored_approval.approval_id
        for stored_approval in repository.list_approvals(proposal_id="pp_002")
    ] == ["pap_010"]


def test_import_psycopg_returns_driver_and_row_factory(monkeypatch):
    fake_psycopg = ModuleType("psycopg")
    fake_psycopg_rows = ModuleType("psycopg.rows")
    fake_dict_row = object()
    fake_psycopg_rows.dict_row = fake_dict_row

    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_psycopg_rows)

    psycopg, dict_row = postgres_module._import_psycopg()
    assert psycopg is fake_psycopg
    assert dict_row is fake_dict_row


def test_postgres_repository_connect_uses_dsn_and_row_factory(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeDriver:
        def connect(self, dsn, row_factory):  # noqa: ANN001
            captured["dsn"] = dsn
            captured["row_factory"] = row_factory
            return "connected"

    fake_row_factory = object()
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (_FakeDriver(), fake_row_factory),
    )

    repository = object.__new__(PostgresProposalRepository)
    repository._dsn = "postgresql://user:pass@localhost:5432/proposals"
    connected = repository._connect()
    assert connected == "connected"
    assert captured["dsn"] == repository._dsn
    assert captured["row_factory"] is fake_row_factory


def test_to_proposal_returns_none_for_missing_row():
    assert postgres_module._to_proposal(None) is None
