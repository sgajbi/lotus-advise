from datetime import datetime, timezone

import src.infrastructure.proposals.postgres as postgres_module
from src.core.proposals.models import ProposalAsyncOperationRecord, ProposalIdempotencyRecord
from src.infrastructure.proposals.postgres import PostgresProposalRepository


class _FakeCursor:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self):
        self.idempotency = {}
        self.operations = {}

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if sql.startswith("CREATE TABLE"):
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
        raise AssertionError(f"Unhandled SQL in fake connection: {sql}")

    def commit(self):
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


def test_postgres_repository_unimplemented_methods_report_stable_error(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    try:
        repository.get_proposal(proposal_id="pp_missing")
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_NOT_IMPLEMENTED"
    else:
        raise AssertionError(
            "Expected PROPOSAL_POSTGRES_NOT_IMPLEMENTED for missing parity methods"
        )
