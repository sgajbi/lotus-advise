from fastapi.testclient import TestClient

from src.api.main import app


def test_create_stateful_workspace_session_returns_workspace_context():
    payload = {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_growth_01",
        },
    }

    with TestClient(app) as client:
        response = client.post("/advisory/workspaces", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["workspace"]["workspace_id"].startswith("aws_")
    assert body["workspace"]["input_mode"] == "stateful"
    assert body["workspace"]["stateful_input"]["portfolio_id"] == "pf_advisory_01"
    assert body["workspace"]["resolved_context"]["portfolio_id"] == "pf_advisory_01"
    assert body["workspace"]["evaluation_summary"] is None


def test_create_stateless_workspace_session_returns_snapshot_context():
    payload = {
        "workspace_name": "Sandbox drift review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "snapshot_id": "ps_001",
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [],
                },
                "market_data_snapshot": {
                    "snapshot_id": "md_001",
                    "prices": [],
                    "fx_rates": [],
                },
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        response = client.post("/advisory/workspaces", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["workspace"]["input_mode"] == "stateless"
    assert body["workspace"]["resolved_context"]["portfolio_snapshot_id"] == "ps_001"
    assert body["workspace"]["resolved_context"]["market_data_snapshot_id"] == "md_001"


def test_create_workspace_rejects_mixed_mode_payloads():
    payload = {
        "workspace_name": "Bad mixed workspace",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "as_of": "2026-03-25",
        },
    }

    with TestClient(app) as client:
        response = client.post("/advisory/workspaces", json=payload)

    assert response.status_code == 422
