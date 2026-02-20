from datetime import datetime, timezone

import src.infrastructure.proposals.postgres as postgres_module
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalIdempotencyRecord,
    ProposalRecord,
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
        if "INSERT INTO proposal_async_operations" in sql:
            self.operations[args[0]] = {
                "operation_id": args[0],
                "operation_type": args[1],
                "status": args[2],
                "correlation_id": args[3],
                "idempotency_key": args[4],
                "proposal_id": args[5],
                "created_by": args[6],
                "created_at": args[7],
                "started_at": args[8],
                "finished_at": args[9],
                "result_json": args[10],
                "error_json": args[11],
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
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    repository.create_operation(operation)

    loaded = repository.get_operation(operation_id="pop_001")
    assert loaded is not None
    assert loaded.status == "PENDING"
    assert loaded.result_json is None
    assert loaded.error_json is None

    operation.status = "SUCCEEDED"
    operation.proposal_id = "pp_001"
    operation.started_at = created_at
    operation.finished_at = created_at
    operation.result_json = {"proposal": {"proposal_id": "pp_001"}}
    operation.error_json = None
    repository.update_operation(operation)

    by_operation = repository.get_operation(operation_id="pop_001")
    assert by_operation is not None
    assert by_operation.status == "SUCCEEDED"
    assert by_operation.proposal_id == "pp_001"
    assert by_operation.result_json == {"proposal": {"proposal_id": "pp_001"}}
    assert by_operation.error_json is None
    assert by_operation.started_at == created_at
    assert by_operation.finished_at == created_at

    by_correlation = repository.get_operation_by_correlation(correlation_id="corr-prop-1")
    assert by_correlation is not None
    assert by_correlation.operation_id == "pop_001"
    assert by_correlation.status == "SUCCEEDED"


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
