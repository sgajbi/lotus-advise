from pathlib import Path

import pytest

from src.infrastructure.policy_packs.postgres_state import PostgresPolicyEvaluationStateStore

REPO_ROOT = Path(__file__).resolve().parents[4]
POSTGRES_REPOSITORY = REPO_ROOT / "src" / "infrastructure" / "policy_packs" / "postgres.py"
POSTGRES_STATE_HELPER = REPO_ROOT / "src" / "infrastructure" / "policy_packs" / "postgres_state.py"


class _Cursor:
    rowcount = 1


class _Connection:
    def __init__(self, *, fail_statement: str | None = None) -> None:
        self.fail_statement = fail_statement
        self.executed: list[str] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        self.executed.append(sql)
        if self.fail_statement and self.fail_statement in sql:
            raise RuntimeError("policy persistence failed")
        return _Cursor()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_policy_pack_postgres_repository_remains_delegating_adapter() -> None:
    source = POSTGRES_REPOSITORY.read_text(encoding="utf-8")

    assert "INSERT INTO" not in source
    assert "SELECT" not in source
    assert "FROM policy_" not in source
    assert "ON CONFLICT" not in source
    assert "apply_postgres_migrations" in source
    assert 'namespace="policy_packs"' in source


def test_policy_pack_postgres_state_helper_owns_sql_mapping() -> None:
    source = POSTGRES_STATE_HELPER.read_text(encoding="utf-8")

    assert "policy_evaluation_records" in source
    assert "policy_evaluation_audit_events" in source
    assert "policy_evaluation_idempotency" in source
    assert "policy_pack_catalog_versions" in source
    assert "policy_pack_catalog_audit_events" in source
    assert "policy_pack_catalog_idempotency" in source


def test_policy_pack_postgres_state_helper_guards_transactional_writes() -> None:
    source = POSTGRES_STATE_HELPER.read_text(encoding="utf-8")

    assert "connection.rollback()" in source
    assert "POLICY_EVALUATION_IDEMPOTENCY_KEY_CONFLICT" in source
    assert "POLICY_PACK_IDEMPOTENCY_KEY_CONFLICT" in source
    assert "policy_evaluation_idempotency.request_hash = excluded.request_hash" in source
    assert "policy_pack_catalog_idempotency.request_hash = excluded.request_hash" in source
    assert "policy_evaluation_audit_events.request_hash = excluded.request_hash" in source
    assert "policy_pack_catalog_audit_events.request_hash = excluded.request_hash" in source
    assert "SELECT COUNT(*) FROM policy_evaluation_audit_events" in " ".join(source.split())
    assert "SELECT COUNT(*) FROM policy_pack_catalog_audit_events" in " ".join(source.split())


def test_policy_evaluation_postgres_snapshot_save_rolls_back_on_partial_failure() -> None:
    connection = _Connection(fail_statement="INSERT INTO policy_evaluation_audit_events")
    store = PostgresPolicyEvaluationStateStore(connect=lambda: connection)

    with pytest.raises(RuntimeError, match="policy persistence failed"):
        store.save_snapshot(_policy_evaluation_snapshot())

    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert connection.closed is True


def _policy_evaluation_snapshot() -> dict:
    record = {
        "evaluation_id": "pev_txn_001",
        "proposal_id": "pp_txn_001",
        "proposal_version_id": "ppv_txn_001",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "policy_pack_id": "SG_PRIVATE_BANKING_REFERENCE",
        "policy_version": "2026.05",
        "generated_at": "2026-05-26T00:00:00+00:00",
        "created_by": "advisor_1",
        "evaluation_status": "PENDING_REVIEW",
        "policy_content_hash": "sha256:policy",
        "source_evidence_hash": "sha256:source",
        "evaluation_hash": "sha256:evaluation",
        "rule_result_hashes": {},
        "evaluation_json": {},
        "source_refs": [],
        "source_gaps": [],
        "approval_dependencies": [],
        "disclosure_requirements": [],
        "consent_requirements": [],
        "review_events_json": [],
        "sign_off_events_json": [],
        "report_archive_refs_json": [],
        "replay_metadata_json": {},
    }
    event = {
        "event_id": "peev_000001",
        "evaluation_id": "pev_txn_001",
        "proposal_id": "pp_txn_001",
        "proposal_version_id": "ppv_txn_001",
        "event_type": "POLICY_EVALUATION_FINALIZED",
        "actor_id": "advisor_1",
        "occurred_at": "2026-05-26T00:00:00+00:00",
        "content_hash": "sha256:evaluation",
        "idempotency_key": "idem_txn_001",
        "reason_json": {"idempotency_request_hash": "sha256:request"},
    }
    return {
        "records": {"pev_txn_001": record},
        "events": {"pev_txn_001": [event]},
        "idempotency": [
            {
                "idempotency_key": "idem_txn_001",
                "request_hash": "sha256:request",
                "evaluation_id": "pev_txn_001",
                "event_id": "peev_000001",
            }
        ],
        "identity_index": [],
    }
