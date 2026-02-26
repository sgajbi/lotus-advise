import pytest
from fastapi.testclient import TestClient

import src.api.persistence_profile as persistence_profile
from src.api.main import app
from src.api.persistence_profile import (
    app_persistence_profile_name,
    validate_persistence_profile_guardrails,
)


def test_persistence_profile_defaults_to_local(monkeypatch):
    monkeypatch.delenv("APP_PERSISTENCE_PROFILE", raising=False)
    assert app_persistence_profile_name() == "LOCAL"


def test_persistence_profile_unknown_value_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "staging")
    assert app_persistence_profile_name() == "LOCAL"


def test_production_profile_requires_advisory_postgres(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY")

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PROPOSAL_STORE_BACKEND_UNSUPPORTED"


def test_production_profile_requires_advisory_postgres_dsn(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"


def test_production_profile_allows_postgres_backends(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")

    validate_persistence_profile_guardrails()


def test_startup_fails_fast_for_advisory_backend_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PROPOSAL_STORE_BACKEND_UNSUPPORTED"


def test_startup_fails_fast_for_advisory_dsn_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"


def test_profile_guardrails_requires_advisory_postgres_backend_name(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setattr(persistence_profile, "proposal_store_backend_name", lambda: "IN_MEMORY")
    monkeypatch.setattr(
        persistence_profile,
        "proposal_postgres_dsn",
        lambda: "postgresql://u:p@localhost:5432/db",
    )

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES"
