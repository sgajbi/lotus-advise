from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers.dpm_policy_packs import reset_dpm_policy_pack_repository_for_tests


def setup_function() -> None:
    reset_dpm_policy_pack_repository_for_tests()


def test_policy_pack_admin_apis_disabled_by_default():
    with TestClient(app) as client:
        response = client.put(
            "/rebalance/policies/catalog/dpm_standard_v1",
            json={"version": "1"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "DPM_POLICY_PACK_ADMIN_APIS_DISABLED"


def test_policy_pack_admin_apis_env_repository_roundtrip(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "true")
        monkeypatch.delenv("DPM_POLICY_PACK_CATALOG_BACKEND", raising=False)
        reset_dpm_policy_pack_repository_for_tests()

        upsert = client.put(
            "/rebalance/policies/catalog/dpm_standard_v1",
            json={
                "version": "2",
                "turnover_policy": {"max_turnover_pct": "0.15"},
                "idempotency_policy": {"replay_enabled": True},
            },
        )
        assert upsert.status_code == 200
        assert upsert.json()["item"]["policy_pack_id"] == "dpm_standard_v1"
        assert upsert.json()["item"]["version"] == "2"

        get_one = client.get("/rebalance/policies/catalog/dpm_standard_v1")
        assert get_one.status_code == 200
        assert get_one.json()["policy_pack_id"] == "dpm_standard_v1"
        assert get_one.json()["turnover_policy"]["max_turnover_pct"] == "0.15"

        catalog = client.get("/rebalance/policies/catalog")
        assert catalog.status_code == 200
        assert catalog.json()["total"] >= 1
        assert "dpm_standard_v1" in {item["policy_pack_id"] for item in catalog.json()["items"]}

        delete = client.delete("/rebalance/policies/catalog/dpm_standard_v1")
        assert delete.status_code == 204

        get_missing = client.get("/rebalance/policies/catalog/dpm_standard_v1")
        assert get_missing.status_code == 404
        assert get_missing.json()["detail"] == "DPM_POLICY_PACK_NOT_FOUND"
