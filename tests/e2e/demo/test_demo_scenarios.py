"""Advisory demo scenario regression tests."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session
from src.api.routers.proposals import reset_proposal_workflow_service_for_tests

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "demo")


def load_demo_scenario(filename: str) -> dict:
    path = os.path.join(DEMO_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def _override_get_db_session():
    yield None


def _proposal_create_payload(portfolio_id: str) -> dict:
    return {
        "created_by": "advisor_e2e",
        "metadata": {
            "title": "E2E proposal",
            "advisor_notes": "workflow validation",
            "jurisdiction": "SG",
            "mandate_id": "mandate_e2e",
        },
        "simulate_request": {
            "portfolio_snapshot": {
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
                    {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
                ],
                "fx_rates": [],
            },
            "shelf_entries": [
                {"instrument_id": "EQ_OLD", "status": "APPROVED"},
                {"instrument_id": "EQ_NEW", "status": "APPROVED"},
            ],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [{"currency": "USD", "amount": "100"}],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
        },
    }


def test_demo_advisory_async_create_and_lookup_via_api():
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            accepted = client.post(
                "/rebalance/proposals/async",
                json=_proposal_create_payload("pf_demo_async_1"),
                headers={
                    "Idempotency-Key": "demo-36-proposal-async",
                    "X-Correlation-Id": "demo-corr-36-proposal-async",
                },
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            by_operation = client.get(f"/rebalance/proposals/operations/{operation_id}")
            by_correlation = client.get(
                "/rebalance/proposals/operations/by-correlation/demo-corr-36-proposal-async"
            )
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert by_operation.status_code == 200
    assert by_correlation.status_code == 200


def test_demo_advisory_async_version_via_api():
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            created = client.post(
                "/rebalance/proposals",
                json=_proposal_create_payload("pf_demo_async_2"),
                headers={"Idempotency-Key": "demo-37-proposal-async-base"},
            )
            assert created.status_code == 200
            proposal_id = created.json()["proposal"]["proposal_id"]

            accepted = client.post(
                f"/rebalance/proposals/{proposal_id}/versions/async",
                json={
                    "created_by": "advisor_e2e",
                    "metadata": {"title": "E2E async version"},
                    "simulate_request": _proposal_create_payload("pf_demo_async_2")[
                        "simulate_request"
                    ],
                },
                headers={"X-Correlation-Id": "demo-corr-37-proposal-async-version"},
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            operation = client.get(f"/rebalance/proposals/operations/{operation_id}")
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert operation.status_code == 200


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("10_advisory_proposal_simulate.json", "READY"),
        ("11_advisory_auto_funding_single_ccy.json", "READY"),
        ("12_advisory_partial_funding.json", "READY"),
        ("13_advisory_missing_fx_blocked.json", "BLOCKED"),
        ("14_advisory_drift_asset_class.json", "READY"),
        ("15_advisory_drift_instrument.json", "READY"),
        ("16_advisory_suitability_resolved_single_position.json", "READY"),
        ("17_advisory_suitability_new_issuer_breach.json", "READY"),
        ("18_advisory_suitability_sell_only_violation.json", "BLOCKED"),
    ],
)
def test_demo_advisory_scenarios_via_api(filename: str, expected_status: str):
    data = load_demo_scenario(filename)
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            response = client.post(
                "/rebalance/proposals/simulate",
                json=data,
                headers={"Idempotency-Key": f"demo-{filename}"},
            )
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert response.status_code == 200
    assert response.json()["status"] == expected_status


def test_demo_advisory_artifact_scenario_via_api():
    data = load_demo_scenario("19_advisory_proposal_artifact.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        reset_proposal_workflow_service_for_tests()
        try:
            response = client.post(
                "/rebalance/proposals/artifact",
                json=data,
                headers={"Idempotency-Key": "demo-19-advisory-artifact"},
            )
        finally:
            app.dependency_overrides = original_overrides
            reset_proposal_workflow_service_for_tests()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "READY"
    assert body["summary"]["recommended_next_step"] == "CLIENT_CONSENT"
