from src.api.routers import proposals_config


def test_proposal_backend_alias_and_default(monkeypatch):
    monkeypatch.delenv("PROPOSAL_STORE_BACKEND", raising=False)
    assert proposals_config.proposal_store_backend_name() == "IN_MEMORY"

    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    assert proposals_config.proposal_store_backend_name() == "POSTGRES"

    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "unknown")
    assert proposals_config.proposal_store_backend_name() == "IN_MEMORY"


def test_proposal_postgres_dsn(monkeypatch):
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    assert proposals_config.proposal_postgres_dsn() == ""

    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/proposals",
    )
    assert (
        proposals_config.proposal_postgres_dsn()
        == "postgresql://user:pass@localhost:5432/proposals"
    )


def test_build_repository_postgres_requires_dsn(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    try:
        proposals_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing proposal postgres dsn")


def test_build_repository_postgres_not_implemented(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/proposals",
    )
    try:
        proposals_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_NOT_IMPLEMENTED"
    else:
        raise AssertionError("Expected RuntimeError for unimplemented proposal postgres backend")
