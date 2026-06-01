from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
POSTGRES_REPOSITORY = REPO_ROOT / "src" / "infrastructure" / "proposals" / "postgres.py"
POSTGRES_HELPERS = {
    "postgres_approvals.py",
    "postgres_async_operations.py",
    "postgres_cockpit_acknowledgements.py",
    "postgres_idempotency.py",
    "postgres_memos.py",
    "postgres_records.py",
    "postgres_versions.py",
    "postgres_workflow_events.py",
}


def test_proposal_postgres_repository_remains_delegating_adapter() -> None:
    source = POSTGRES_REPOSITORY.read_text(encoding="utf-8")

    assert len(source.splitlines()) < 400
    assert "INSERT INTO" not in source
    assert "SELECT" not in source
    assert "FROM proposal_" not in source
    assert "ON CONFLICT" not in source


def test_proposal_postgres_persistence_helpers_are_explicit_modules() -> None:
    helper_dir = REPO_ROOT / "src" / "infrastructure" / "proposals"
    helper_names = {path.name for path in helper_dir.glob("postgres_*.py")}

    assert POSTGRES_HELPERS <= helper_names


def test_proposal_postgres_helpers_do_not_import_repository_adapter() -> None:
    helper_dir = REPO_ROOT / "src" / "infrastructure" / "proposals"

    for helper_name in POSTGRES_HELPERS:
        source = (helper_dir / helper_name).read_text(encoding="utf-8")
        assert "from src.infrastructure.proposals.postgres import" not in source
        assert "import src.infrastructure.proposals.postgres" not in source
