from typing import Any

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.api.services.workspace_service import reset_workspace_sessions_for_tests


def setup_function() -> None:
    reset_workspace_sessions_for_tests()
    reset_proposal_workflow_service_for_tests()


def _resolved_stateful_context(portfolio_id: str, as_of: str) -> dict[str, Any]:
    return {
        "simulate_request": {
            "portfolio_snapshot": {
                "snapshot_id": f"ps_{portfolio_id}_{as_of}",
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "10000"}],
            },
            "market_data_snapshot": {
                "snapshot_id": f"md_{as_of}",
                "prices": [],
                "fx_rates": [],
            },
            "shelf_entries": [],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [],
        },
        "resolved_context": {
            "portfolio_id": portfolio_id,
            "as_of": as_of,
            "portfolio_snapshot_id": f"ps_{portfolio_id}_{as_of}",
            "market_data_snapshot_id": f"md_{as_of}",
        },
    }


def _normalize_proposal_result_for_parity(body: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        key: value for key, value in body.items() if key not in {"correlation_id", "lineage"}
    }
    lineage = dict(body["lineage"])
    lineage.pop("idempotency_key", None)
    normalized["lineage"] = lineage
    return normalized


def _normalize_created_version_result_for_parity(body: dict[str, Any]) -> dict[str, Any]:
    return _normalize_proposal_result_for_parity(body["version"]["proposal_result"])


def test_create_stateful_workspace_session_returns_workspace_context(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )
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
    assert body["workspace"]["resolved_context"]["portfolio_snapshot_id"] == (
        "ps_pf_advisory_01_2026-03-25"
    )
    assert body["workspace"]["draft_state"]["trade_drafts"] == []
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
    assert body["workspace"]["draft_state"]["trade_drafts"] == []


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


def test_workspace_draft_action_adds_trade_and_reevaluates_stateless_workspace():
    create_payload = {
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
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "snapshot_id": "md_001",
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        create_response = client.post("/advisory/workspaces", json=create_payload)
        workspace_id = create_response.json()["workspace"]["workspace_id"]

        action_response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "2",
                },
            },
        )

    assert action_response.status_code == 200
    body = action_response.json()
    assert len(body["workspace"]["draft_state"]["trade_drafts"]) == 1
    assert body["workspace"]["evaluation_summary"]["status"] == "READY"
    assert body["workspace"]["evaluation_summary"]["impact_summary"]["trade_count"] == 1
    assert body["workspace"]["latest_proposal_result"]["status"] == "READY"


def test_workspace_draft_action_updates_and_removes_trade():
    create_payload = {
        "workspace_name": "Sandbox drift review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        add_body = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "2",
                },
            },
        ).json()
        trade_id = add_body["workspace"]["draft_state"]["trade_drafts"][0]["workspace_trade_id"]

        update_response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "UPDATE_TRADE",
                "workspace_trade_id": trade_id,
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "3",
                },
            },
        )
        remove_response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "REMOVE_TRADE",
                "workspace_trade_id": trade_id,
            },
        )

    assert update_response.status_code == 200
    assert (
        update_response.json()["workspace"]["draft_state"]["trade_drafts"][0]["trade"]["quantity"]
        == "3"
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["workspace"]["draft_state"]["trade_drafts"] == []


def test_workspace_draft_action_updates_and_removes_cash_flow():
    create_payload = {
        "workspace_name": "Sandbox funding review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
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
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        add_body = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_CASH_FLOW",
                "cash_flow": {
                    "direction": "CONTRIBUTION",
                    "amount": "2500",
                    "currency": "USD",
                },
            },
        ).json()
        cash_flow_id = add_body["workspace"]["draft_state"]["cash_flow_drafts"][0][
            "workspace_cash_flow_id"
        ]

        update_response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "UPDATE_CASH_FLOW",
                "workspace_cash_flow_id": cash_flow_id,
                "cash_flow": {
                    "direction": "CONTRIBUTION",
                    "amount": "3000",
                    "currency": "USD",
                },
            },
        )
        remove_response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "REMOVE_CASH_FLOW",
                "workspace_cash_flow_id": cash_flow_id,
            },
        )

    assert update_response.status_code == 200
    assert (
        update_response.json()["workspace"]["draft_state"]["cash_flow_drafts"][0]["cash_flow"][
            "amount"
        ]
        == "3000"
    )
    assert (
        update_response.json()["workspace"]["evaluation_summary"]["impact_summary"][
            "cash_flow_count"
        ]
        == 1
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["workspace"]["draft_state"]["cash_flow_drafts"] == []


def test_workspace_get_returns_latest_workspace_state_after_mutation():
    create_payload = {
        "workspace_name": "Sandbox drift review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "2",
                },
            },
        )
        get_response = client.get(f"/advisory/workspaces/{workspace_id}")

    assert get_response.status_code == 200
    body = get_response.json()
    assert len(body["draft_state"]["trade_drafts"]) == 1
    assert body["evaluation_summary"]["impact_summary"]["trade_count"] == 1


def test_workspace_evaluate_reruns_stateless_workspace_successfully():
    create_payload = {
        "workspace_name": "Sandbox drift review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "2",
                },
            },
        )
        response = client.post(f"/advisory/workspaces/{workspace_id}/evaluate")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_summary"]["status"] == "READY"
    assert body["latest_proposal_result"]["status"] == "READY"


def test_stateless_workspace_evaluate_matches_direct_simulation_for_equivalent_input():
    simulate_request = {
        "portfolio_snapshot": {
            "snapshot_id": "ps_parity_001",
            "portfolio_id": "pf_parity_001",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "10000"}],
        },
        "market_data_snapshot": {
            "snapshot_id": "md_parity_001",
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
        "options": {
            "enable_proposal_simulation": True,
            "enable_workflow_gates": True,
            "enable_suitability_scanner": True,
        },
        "proposed_cash_flows": [{"direction": "CONTRIBUTION", "amount": "250", "currency": "USD"}],
        "proposed_trades": [
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_NEW",
                "quantity": "4",
            }
        ],
    }
    create_payload = {
        "workspace_name": "Parity workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {"simulate_request": simulate_request},
    }

    with TestClient(app) as client:
        simulate_response = client.post(
            "/advisory/proposals/simulate",
            json=simulate_request,
            headers={"Idempotency-Key": "parity-simulate-001"},
        )
        assert simulate_response.status_code == 200

        workspace_create_response = client.post("/advisory/workspaces", json=create_payload)
        assert workspace_create_response.status_code == 201
        workspace_id = workspace_create_response.json()["workspace"]["workspace_id"]

        workspace_evaluate_response = client.post(f"/advisory/workspaces/{workspace_id}/evaluate")
        assert workspace_evaluate_response.status_code == 200

    direct_result = _normalize_proposal_result_for_parity(simulate_response.json())
    workspace_result = _normalize_proposal_result_for_parity(
        workspace_evaluate_response.json()["latest_proposal_result"]
    )

    assert workspace_result == direct_result


def test_workspace_evaluate_uses_stateful_context_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )
    create_payload = {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(f"/advisory/workspaces/{workspace_id}/evaluate")

    assert response.status_code == 200
    assert response.json()["evaluation_summary"]["status"] == "READY"
    assert response.json()["resolved_context"]["portfolio_snapshot_id"] == (
        "ps_pf_advisory_01_2026-03-25"
    )


def test_workspace_endpoints_return_404_for_missing_workspace():
    with TestClient(app) as client:
        get_response = client.get("/advisory/workspaces/aws_missing")
        evaluate_response = client.post("/advisory/workspaces/aws_missing/evaluate")
        save_response = client.post(
            "/advisory/workspaces/aws_missing/save",
            json={"saved_by": "advisor_123"},
        )
        list_response = client.get("/advisory/workspaces/aws_missing/saved-versions")
        handoff_response = client.post(
            "/advisory/workspaces/aws_missing/handoff",
            headers={"Idempotency-Key": "workspace-handoff-idem-missing"},
            json={"handoff_by": "advisor_123"},
        )

    assert get_response.status_code == 404
    assert evaluate_response.status_code == 404
    assert save_response.status_code == 404
    assert list_response.status_code == 404
    assert handoff_response.status_code == 404


def test_workspace_draft_action_not_found_paths_return_404():
    create_payload = {
        "workspace_name": "Sandbox drift review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        update_trade = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "UPDATE_TRADE",
                "workspace_trade_id": "wtd_missing",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "1",
                },
            },
        )
        remove_cash_flow = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "REMOVE_CASH_FLOW",
                "workspace_cash_flow_id": "wcf_missing",
            },
        )

    assert update_trade.status_code == 404
    assert update_trade.json()["detail"] == "WORKSPACE_TRADE_NOT_FOUND"
    assert remove_cash_flow.status_code == 404
    assert remove_cash_flow.json()["detail"] == "WORKSPACE_CASH_FLOW_NOT_FOUND"


def test_workspace_draft_action_replace_options_rejects_stateful_workspace_without_resolution():
    create_payload = {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "REPLACE_OPTIONS",
                "options": {"enable_proposal_simulation": True, "auto_funding": False},
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "WORKSPACE_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE"


def test_workspace_draft_action_replace_options_uses_stateful_context_resolution(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )
    create_payload = {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "REPLACE_OPTIONS",
                "options": {"enable_proposal_simulation": True, "auto_funding": False},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["workspace"]["draft_state"]["options"]["auto_funding"] is False
    assert body["workspace"]["resolved_context"]["portfolio_snapshot_id"] == (
        "ps_pf_advisory_01_2026-03-25"
    )


def test_workspace_save_list_resume_and_compare_saved_versions():
    create_payload = {
        "workspace_name": "Sandbox compare review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        initial_action = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "2",
                },
            },
        ).json()
        save_response = client.post(
            f"/advisory/workspaces/{workspace_id}/save",
            json={"saved_by": "advisor_123", "version_label": "Initial sandbox draft"},
        )
        saved_version_id = save_response.json()["saved_version"]["workspace_version_id"]
        client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_CASH_FLOW",
                "cash_flow": {
                    "direction": "CONTRIBUTION",
                    "amount": "3000",
                    "currency": "USD",
                },
            },
        )
        compare_response = client.post(
            f"/advisory/workspaces/{workspace_id}/compare",
            json={"workspace_version_id": saved_version_id},
        )
        list_response = client.get(f"/advisory/workspaces/{workspace_id}/saved-versions")
        resume_response = client.post(
            f"/advisory/workspaces/{workspace_id}/resume",
            json={"actor_id": "advisor_123", "workspace_version_id": saved_version_id},
        )

    assert initial_action["workspace"]["evaluation_summary"]["impact_summary"]["trade_count"] == 1
    assert save_response.status_code == 200
    assert save_response.json()["workspace"]["saved_version_count"] == 1
    assert (
        save_response.json()["workspace"]["latest_saved_version"]["version_label"]
        == "Initial sandbox draft"
    )
    assert save_response.json()["saved_version"]["replay_evidence"]["evaluation_request_hash"]
    assert compare_response.status_code == 200
    assert compare_response.json()["diff_summary"]["trade_count_delta"] == 0
    assert compare_response.json()["diff_summary"]["cash_flow_count_delta"] == 1
    assert list_response.status_code == 200
    assert len(list_response.json()["saved_versions"]) == 1
    assert list_response.json()["saved_versions"][0]["workspace_version_id"] == saved_version_id
    assert resume_response.status_code == 200
    assert resume_response.json()["draft_state"]["cash_flow_drafts"] == []
    assert resume_response.json()["evaluation_summary"]["impact_summary"]["trade_count"] == 1


def test_workspace_resume_and_compare_missing_saved_version_return_404():
    create_payload = {
        "workspace_name": "Sandbox compare review",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        resume_response = client.post(
            f"/advisory/workspaces/{workspace_id}/resume",
            json={"actor_id": "advisor_123", "workspace_version_id": "awv_missing"},
        )
        compare_response = client.post(
            f"/advisory/workspaces/{workspace_id}/compare",
            json={"workspace_version_id": "awv_missing"},
        )

    assert resume_response.status_code == 404
    assert resume_response.json()["detail"] == "WORKSPACE_SAVED_VERSION_NOT_FOUND"
    assert compare_response.status_code == 404
    assert compare_response.json()["detail"] == "WORKSPACE_SAVED_VERSION_NOT_FOUND"


def test_workspace_resume_and_compare_missing_workspace_return_404():
    with TestClient(app) as client:
        resume_response = client.post(
            "/advisory/workspaces/aws_missing/resume",
            json={"actor_id": "advisor_123", "workspace_version_id": "awv_001"},
        )
        compare_response = client.post(
            "/advisory/workspaces/aws_missing/compare",
            json={"workspace_version_id": "awv_001"},
        )

    assert resume_response.status_code == 404
    assert compare_response.status_code == 404


def test_workspace_handoff_creates_proposal_then_new_version_without_duplicating_lifecycle():
    create_payload = {
        "workspace_name": "Growth rotation workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_1",
                    "quantity": "2",
                },
            },
        )
        first_handoff = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            headers={"Idempotency-Key": "workspace-handoff-idem-001"},
            json={
                "handoff_by": "advisor_123",
                "metadata": {
                    "title": "Q2 2026 growth reallocation proposal",
                    "jurisdiction": "SG",
                    "mandate_id": "mandate_growth_01",
                },
            },
        )
        client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_123",
                "action_type": "ADD_CASH_FLOW",
                "cash_flow": {
                    "direction": "CONTRIBUTION",
                    "amount": "1500",
                    "currency": "USD",
                },
            },
        )
        second_handoff = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            json={"handoff_by": "advisor_123"},
        )

    assert first_handoff.status_code == 200
    first_body = first_handoff.json()
    assert first_body["handoff_action"] == "CREATED_PROPOSAL"
    proposal_id = first_body["proposal"]["proposal"]["proposal_id"]
    assert first_body["proposal"]["proposal"]["lifecycle_origin"] == "WORKSPACE_HANDOFF"
    assert first_body["proposal"]["proposal"]["source_workspace_id"] == workspace_id
    assert first_body["workspace"]["lifecycle_link"]["proposal_id"] == proposal_id
    assert first_body["proposal"]["version"]["version_no"] == 1

    assert second_handoff.status_code == 200
    second_body = second_handoff.json()
    assert second_body["handoff_action"] == "CREATED_PROPOSAL_VERSION"
    assert second_body["proposal"]["proposal"]["proposal_id"] == proposal_id
    assert second_body["proposal"]["proposal"]["lifecycle_origin"] == "WORKSPACE_HANDOFF"
    assert second_body["proposal"]["proposal"]["source_workspace_id"] == workspace_id
    assert second_body["proposal"]["version"]["version_no"] == 2
    assert second_body["workspace"]["lifecycle_link"]["current_version_no"] == 2


def test_workspace_handoff_requires_idempotency_key_for_first_create():
    create_payload = {
        "workspace_name": "Growth rotation workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            json={"handoff_by": "advisor_123"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "WORKSPACE_HANDOFF_IDEMPOTENCY_KEY_REQUIRED"


def test_workspace_handoff_uses_stateful_context_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )
    create_payload = {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            headers={"Idempotency-Key": "workspace-handoff-idem-002"},
            json={"handoff_by": "advisor_123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["proposal"]["proposal"]["lifecycle_origin"] == "WORKSPACE_HANDOFF"
    assert body["workspace"]["resolved_context"]["portfolio_snapshot_id"] == (
        "ps_pf_advisory_01_2026-03-25"
    )


def test_stateless_workspace_handoff_matches_direct_proposal_create_for_equivalent_input():
    simulate_request = {
        "portfolio_snapshot": {
            "snapshot_id": "ps_handoff_parity_001",
            "portfolio_id": "pf_handoff_parity_001",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "10000"}],
        },
        "market_data_snapshot": {
            "snapshot_id": "md_handoff_parity_001",
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
        "options": {
            "enable_proposal_simulation": True,
            "enable_workflow_gates": True,
            "enable_suitability_scanner": True,
        },
        "proposed_cash_flows": [{"direction": "CONTRIBUTION", "amount": "250", "currency": "USD"}],
        "proposed_trades": [
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_NEW",
                "quantity": "4",
            }
        ],
    }
    metadata = {
        "title": "Parity handoff proposal",
        "advisor_notes": "Workspace and lifecycle create should match.",
        "jurisdiction": "SG",
        "mandate_id": "mandate_parity_001",
    }
    direct_create_payload = {
        "created_by": "advisor_123",
        "simulate_request": simulate_request,
        "metadata": metadata,
    }
    workspace_create_payload = {
        "workspace_name": "Parity handoff workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {"simulate_request": simulate_request},
    }

    with TestClient(app) as client:
        direct_create_response = client.post(
            "/advisory/proposals",
            json=direct_create_payload,
            headers={"Idempotency-Key": "parity-direct-create-001"},
        )
        assert direct_create_response.status_code == 200

        workspace_create_response = client.post(
            "/advisory/workspaces",
            json=workspace_create_payload,
        )
        assert workspace_create_response.status_code == 201
        workspace_id = workspace_create_response.json()["workspace"]["workspace_id"]

        workspace_handoff_response = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            headers={"Idempotency-Key": "parity-workspace-handoff-001"},
            json={"handoff_by": "advisor_123", "metadata": metadata},
        )
        assert workspace_handoff_response.status_code == 200

    direct_body = direct_create_response.json()
    handoff_body = workspace_handoff_response.json()["proposal"]

    assert _normalize_created_version_result_for_parity(handoff_body) == (
        _normalize_created_version_result_for_parity(direct_body)
    )
    assert handoff_body["version"]["request_hash"] == direct_body["version"]["request_hash"]
    assert handoff_body["version"]["simulation_hash"] == direct_body["version"]["simulation_hash"]
    assert handoff_body["version"]["artifact_hash"].startswith("sha256:")
    assert direct_body["version"]["artifact_hash"].startswith("sha256:")
    assert handoff_body["proposal"]["portfolio_id"] == direct_body["proposal"]["portfolio_id"]
    assert handoff_body["proposal"]["current_version_no"] == 1
    assert handoff_body["proposal"]["lifecycle_origin"] == "WORKSPACE_HANDOFF"


def test_workspace_handoff_returns_422_when_proposal_simulation_flag_is_disabled():
    create_payload = {
        "workspace_name": "Growth rotation workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": False},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            headers={"Idempotency-Key": "workspace-handoff-idem-003"},
            json={"handoff_by": "advisor_123"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true"
    )


def test_workspace_ai_rationale_returns_evidence_grounded_output(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.api.main.generate_workspace_rationale_with_lotus_ai",
        lambda request, evidence: {
            "assistant_output": (
                f"{request.requested_by} requested a rationale "
                f"for workspace {evidence.workspace_id}"
            ),
            "generated_by": "lotus-ai",
            "evidence": evidence.model_dump(mode="json"),
        },
        raising=False,
    )
    create_payload = {
        "workspace_name": "AI rationale workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_ai_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        client.post(f"/advisory/workspaces/{workspace_id}/evaluate")
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/assistant/rationale",
            json={
                "requested_by": "advisor_123",
                "instruction": "Summarize the proposal rationale for an advisor review note.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] == "lotus-ai"
    assert body["evidence"]["workspace_id"] == workspace_id
    assert body["evidence"]["proposal_status"] == "READY"


def test_workspace_ai_rationale_requires_evaluated_workspace() -> None:
    create_payload = {
        "workspace_name": "AI rationale workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_ai_02",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/assistant/rationale",
            json={
                "requested_by": "advisor_123",
                "instruction": "Summarize the proposal rationale for an advisor review note.",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "WORKSPACE_AI_REQUIRES_EVALUATED_WORKSPACE"


def test_workspace_ai_rationale_returns_503_when_lotus_ai_is_unavailable() -> None:
    create_payload = {
        "workspace_name": "AI rationale workspace",
        "created_by": "advisor_123",
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_ai_03",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "10000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        },
    }

    with TestClient(app) as client:
        workspace_id = client.post("/advisory/workspaces", json=create_payload).json()["workspace"][
            "workspace_id"
        ]
        client.post(f"/advisory/workspaces/{workspace_id}/evaluate")
        response = client.post(
            f"/advisory/workspaces/{workspace_id}/assistant/rationale",
            json={
                "requested_by": "advisor_123",
                "instruction": "Summarize the proposal rationale for an advisor review note.",
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "LOTUS_AI_RATIONALE_UNAVAILABLE"
