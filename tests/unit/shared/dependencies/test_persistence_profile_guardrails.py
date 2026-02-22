import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.persistence_profile import (
    app_persistence_profile_name,
    policy_pack_catalog_required_in_profile,
    validate_persistence_profile_guardrails,
)


def test_persistence_profile_defaults_to_local(monkeypatch):
    monkeypatch.delenv("APP_PERSISTENCE_PROFILE", raising=False)
    assert app_persistence_profile_name() == "LOCAL"


def test_persistence_profile_unknown_value_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "staging")
    assert app_persistence_profile_name() == "LOCAL"


def test_policy_pack_catalog_not_required_by_default(monkeypatch):
    monkeypatch.delenv("DPM_POLICY_PACKS_ENABLED", raising=False)
    monkeypatch.delenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", raising=False)
    assert policy_pack_catalog_required_in_profile() is False


def test_production_profile_requires_dpm_postgres(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "IN_MEMORY")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES"


def test_production_profile_requires_advisory_postgres(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES"


def test_production_profile_requires_policy_pack_postgres_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "ENV_JSON")

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES"


def test_production_profile_allows_postgres_backends(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")

    validate_persistence_profile_guardrails()


def test_production_profile_requires_dpm_postgres_dsn(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN"


def test_production_profile_requires_advisory_postgres_dsn(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"


def test_production_profile_requires_policy_pack_postgres_dsn(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError) as exc:
        validate_persistence_profile_guardrails()
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN"


def test_startup_fails_fast_for_production_profile_misconfiguration(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "IN_MEMORY")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES"


def test_startup_fails_fast_for_advisory_backend_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES"


def test_startup_fails_fast_for_policy_pack_backend_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "ENV_JSON")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES"


def test_startup_fails_fast_for_dpm_dsn_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN"


def test_startup_fails_fast_for_advisory_dsn_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "false")
    monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "false")

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"


def test_startup_fails_fast_for_policy_pack_dsn_in_production(monkeypatch):
    monkeypatch.setenv("APP_PERSISTENCE_PROFILE", "PRODUCTION")
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("DPM_POLICY_PACKS_ENABLED", "true")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN"
