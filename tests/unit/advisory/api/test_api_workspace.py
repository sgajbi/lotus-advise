from fastapi.testclient import TestClient

from src.api.main import app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.api.services.workspace_service import reset_workspace_sessions_for_tests


def setup_function() -> None:
    reset_workspace_sessions_for_tests()
    reset_proposal_workflow_service_for_tests()


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


def test_workspace_evaluate_rejects_stateful_session_until_stateful_resolution_exists():
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

    assert response.status_code == 409
    assert response.json()["detail"] == "WORKSPACE_STATEFUL_EVALUATION_NOT_IMPLEMENTED"


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
    assert response.json()["detail"] == "WORKSPACE_STATEFUL_EVALUATION_NOT_IMPLEMENTED"


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
    assert first_body["workspace"]["lifecycle_link"]["proposal_id"] == proposal_id
    assert first_body["proposal"]["version"]["version_no"] == 1

    assert second_handoff.status_code == 200
    second_body = second_handoff.json()
    assert second_body["handoff_action"] == "CREATED_PROPOSAL_VERSION"
    assert second_body["proposal"]["proposal"]["proposal_id"] == proposal_id
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


def test_workspace_handoff_rejects_stateful_workspace_until_stateful_resolution_exists():
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

    assert response.status_code == 409
    assert response.json()["detail"] == "WORKSPACE_STATEFUL_EVALUATION_NOT_IMPLEMENTED"


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
