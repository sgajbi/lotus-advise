from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers.dpm_policy_packs import reset_dpm_policy_pack_repository_for_tests


def setup_function() -> None:
    reset_dpm_policy_pack_repository_for_tests()


def test_policy_pack_catalog_postgres_requires_dsn(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
        monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)
        monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
        reset_dpm_policy_pack_repository_for_tests()

        response = client.get("/rebalance/policies/catalog")
        assert response.status_code == 503
        assert response.json()["detail"] == "DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED"
