from fastapi.testclient import TestClient

from src.api.main import app


def _payload() -> dict:
    return {
        "tactical_view": {
            "tactical_view_id": "thv_2026_05_asia_duration",
            "tactical_view_version": "2026.05",
            "theme_id": "asia_duration_reduce",
            "as_of_date": "2026-05-14",
            "target_action": "REDUCE",
            "rationale": "Reduce duration exposure in Asia balanced discretionary books.",
            "source_refs": [
                {
                    "source_system": "lotus-advise",
                    "source_type": "TACTICAL_HOUSE_VIEW",
                    "source_id": "thv_2026_05_asia_duration",
                    "source_version": "2026.05",
                    "content_hash": "sha256:house-view",
                }
            ],
        },
        "candidate_portfolios": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "portfolio_type": "DPM",
                "discretionary_mandate": True,
                "booking_center_code": "Singapore",
                "current_exposure_weight": "0.18",
                "alignment_signal": "OVERWEIGHT",
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "HoldingsAsOf",
                        "source_id": "holdings:PB_SG_GLOBAL_BAL_001:2026-05-14",
                        "source_version": "v1",
                        "content_hash": "sha256:holdings",
                    }
                ],
            }
        ],
        "eligible_portfolio_types": ["DPM"],
        "correlation_id": "corr-thv-001",
    }


def test_tactical_house_view_api_returns_source_owned_cohort() -> None:
    with TestClient(app) as client:
        response = client.post("/advisory/tactical-house-view/cohorts/evaluate", json=_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_name"] == "TacticalHouseViewAffectedCohort"
    assert payload["product_version"] == "v1"
    assert payload["supportability"]["state"] == "READY"
    assert payload["supportability"]["evaluated_candidate_count"] == 1
    assert payload["supportability"]["affected_count"] == 1
    assert payload["supportability"]["excluded_count"] == 0
    assert payload["affected_portfolios"][0]["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert payload["excluded_portfolios"] == []
    assert payload["cohort_id"].startswith("sha256:")
    assert payload["content_hash"].startswith("sha256:")


def test_tactical_house_view_api_validates_candidate_source_refs() -> None:
    payload = _payload()
    payload["candidate_portfolios"][0]["source_refs"] = []

    with TestClient(app) as client:
        response = client.post("/advisory/tactical-house-view/cohorts/evaluate", json=payload)

    assert response.status_code == 422


def test_tactical_house_view_openapi_documents_route_and_boundaries() -> None:
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    route = openapi["paths"]["/advisory/tactical-house-view/cohorts/evaluate"]["post"]
    assert route["summary"] == "Evaluate tactical house-view affected cohort"
    assert "does not discover the global portfolio universe" in route["description"]
    schemas = openapi["components"]["schemas"]
    assert "TacticalHouseViewAffectedCohort" in schemas
    assert (
        schemas["TacticalHouseViewAffectedCohort"]["properties"]["product_name"]["default"]
        == "TacticalHouseViewAffectedCohort"
    )
