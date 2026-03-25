import pytest
from fastapi.testclient import TestClient

import src.api.runtime_persistence as runtime_persistence
from src.api.main import app
from src.api.runtime_persistence import validate_advisory_runtime_persistence


def test_runtime_requires_advisory_postgres_backend(monkeypatch):
    monkeypatch.setattr(runtime_persistence, "proposal_store_backend_name", lambda: "IN_MEMORY")
    monkeypatch.setattr(
        runtime_persistence,
        "proposal_postgres_dsn",
        lambda: "postgresql://u:p@localhost:5432/db",
    )

    with pytest.raises(RuntimeError) as exc:
        validate_advisory_runtime_persistence()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES"


def test_runtime_requires_advisory_postgres_dsn(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError) as exc:
        validate_advisory_runtime_persistence()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"


def test_runtime_allows_postgres_backends(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")

    validate_advisory_runtime_persistence()


def test_startup_fails_fast_for_advisory_backend(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PROPOSAL_STORE_BACKEND_UNSUPPORTED"


def test_startup_fails_fast_for_advisory_dsn(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"


def test_startup_fails_fast_when_proposal_repository_boot_fails(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setattr(
        "src.api.main.ensure_proposal_runtime_ready",
        lambda: (_ for _ in ()).throw(RuntimeError("PROPOSAL_POSTGRES_CONNECTION_FAILED")),
    )

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PROPOSAL_POSTGRES_CONNECTION_FAILED"
