from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app
from src.api.routers.proposals import reset_proposal_workflow_service_for_tests


def _base_create_payload(portfolio_id: str = "pf_integration_proposal_1") -> dict:
    return {
        "created_by": "advisor_integration",
        "metadata": {
            "title": "Integration proposal",
            "advisor_notes": "integration coverage",
            "jurisdiction": "SG",
            "mandate_id": "mandate_integration",
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


def setup_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()


def teardown_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()


def test_proposal_create_list_get_and_version_roundtrip() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload(),
            headers={"Idempotency-Key": "integration-proposal-create-1"},
        )
        assert created.status_code == 200
        created_body = created.json()
        proposal_id = created_body["proposal"]["proposal_id"]

        listed = client.get(
            "/rebalance/proposals",
            params={"portfolio_id": "pf_integration_proposal_1"},
        )
        detail = client.get(f"/rebalance/proposals/{proposal_id}")
        version = client.get(f"/rebalance/proposals/{proposal_id}/versions/1")
        workflow_events = client.get(f"/rebalance/proposals/{proposal_id}/workflow-events")

    assert listed.status_code == 200
    assert detail.status_code == 200
    assert version.status_code == 200
    assert workflow_events.status_code == 200
    assert listed.json()["items"][0]["proposal_id"] == proposal_id
    assert detail.json()["proposal"]["proposal_id"] == proposal_id
    assert version.json()["version_no"] == 1
    assert workflow_events.json()["events"][0]["event_type"] == "CREATED"


def test_proposal_submit_and_support_endpoints() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload("pf_integration_proposal_2"),
            headers={"Idempotency-Key": "integration-proposal-submit-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        submit = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {"comment": "integration submit"},
            },
        )
        approvals = client.get(f"/rebalance/proposals/{proposal_id}/approvals")
        lineage = client.get(f"/rebalance/proposals/{proposal_id}/lineage")

    assert submit.status_code == 200
    assert approvals.status_code == 200
    assert lineage.status_code == 200
    assert submit.json()["current_state"] == "RISK_REVIEW"
