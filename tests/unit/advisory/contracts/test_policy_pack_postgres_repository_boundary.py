from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
POSTGRES_REPOSITORY = REPO_ROOT / "src" / "infrastructure" / "policy_packs" / "postgres.py"
POSTGRES_STATE_HELPER = REPO_ROOT / "src" / "infrastructure" / "policy_packs" / "postgres_state.py"


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
