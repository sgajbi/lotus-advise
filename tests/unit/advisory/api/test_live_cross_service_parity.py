from decimal import Decimal
from typing import Any

import pytest

from scripts.live_runtime_proposal_alternatives import extract_live_proposal_alternatives_snapshot
from scripts.validate_cross_service_parity_live import (
    PortfolioParityScenario,
    _assert_workspace_flow,
    _security_trade_changes_from_proposal_body,
    _select_changed_state_security,
    _select_cross_currency_changed_state_security,
    _select_non_held_changed_state_security,
)


def test_select_changed_state_security_prefers_highest_weight_non_cash_position() -> None:
    positions = [
        {"security_id": "CASH_USD_BOOK_OPERATING", "asset_class": "Cash", "weight": "0.20"},
        {"security_id": "FO_BOND_LOW", "asset_class": "Fixed Income", "weight": "0.08"},
        {"security_id": "FO_FUND_HIGH", "asset_class": "Fund", "weight": "0.24"},
    ]

    selected = _select_changed_state_security(positions)

    assert selected == "FO_FUND_HIGH"


def test_security_trade_changes_from_proposal_body_preserves_trade_quantities_and_notional() -> (
    None
):
    proposal_body = {
        "intents": [
            {
                "intent_type": "SECURITY_TRADE",
                "intent_id": "oi_1",
                "instrument_id": "FO_BOND_UST_2030",
                "side": "BUY",
                "quantity": "1",
                "notional": {"amount": "101.35", "currency": "USD"},
            },
            {
                "intent_type": "SECURITY_TRADE",
                "intent_id": "oi_2",
                "instrument_id": "FO_BOND_SIEMENS_2031",
                "side": "SELL",
                "quantity": "2",
            },
            {
                "intent_type": "CASH_FLOW",
                "intent_id": "oi_3",
            },
        ]
    }

    changes = _security_trade_changes_from_proposal_body(proposal_body)

    assert changes == [
        {
            "security_id": "FO_BOND_UST_2030",
            "transaction_type": "BUY",
            "quantity": Decimal("1"),
            "amount": Decimal("101.35"),
            "currency": "USD",
            "metadata": {
                "proposal_intent_id": "oi_1",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        },
        {
            "security_id": "FO_BOND_SIEMENS_2031",
            "transaction_type": "SELL",
            "quantity": Decimal("2"),
            "metadata": {
                "proposal_intent_id": "oi_2",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        },
    ]


def test_select_cross_currency_changed_state_security_prefers_highest_weight_non_base_holding() -> (
    None
):
    positions = [
        {"security_id": "FO_USD", "asset_class": "Fund", "currency": "USD", "weight": "0.18"},
        {
            "security_id": "FO_EUR_LOW",
            "asset_class": "Bond",
            "currency": "EUR",
            "weight": "0.04",
        },
        {
            "security_id": "FO_EUR_HIGH",
            "asset_class": "Equity",
            "currency": "EUR",
            "weight": "0.16",
        },
        {"security_id": "CASH_EUR", "asset_class": "Cash", "currency": "EUR", "weight": "0.20"},
    ]

    selected = _select_cross_currency_changed_state_security(positions, base_currency="USD")

    assert selected == "FO_EUR_HIGH"


def test_select_non_held_changed_state_security_prefers_known_non_held_candidate() -> None:
    positions = [
        {"security_id": "FO_FUND_PIMCO_INC"},
        {"security_id": "FO_FUND_BLK_ALLOC"},
        {"security_id": "FO_BOND_UST_2030"},
    ]

    selected = _select_non_held_changed_state_security(
        positions,
        candidates=("FO_FUND_PIMCO_INC", "SEC_FUND_EM_EQ", "FO_BOND_UST_2030"),
    )

    assert selected == "SEC_FUND_EM_EQ"


def test_extract_live_proposal_alternatives_snapshot_summarizes_ranked_and_rejected_paths() -> None:
    snapshot = extract_live_proposal_alternatives_snapshot(
        {
            "proposal_alternatives": {
                "requested_objectives": ["REDUCE_CONCENTRATION", "RAISE_CASH"],
                "selected_alternative_id": "alt_reduce",
                "alternatives": [
                    {
                        "alternative_id": "alt_reduce",
                        "objective": "REDUCE_CONCENTRATION",
                        "status": "FEASIBLE",
                        "rank": 1,
                        "selected": True,
                        "ranking_projection": {
                            "ranking_reason_codes": [
                                "STATUS_FEASIBLE",
                                "LOWER_TURNOVER_TIEBREAKER",
                            ]
                        },
                    },
                    {
                        "alternative_id": "alt_cash",
                        "objective": "RAISE_CASH",
                        "status": "FEASIBLE_WITH_REVIEW",
                        "rank": 2,
                        "selected": False,
                    },
                ],
                "rejected_candidates": [
                    {"reason_code": "ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE"}
                ],
            }
        },
        path_name="alternatives_path",
        latency_ms=321.0,
    )

    assert snapshot.requested_objectives == ("REDUCE_CONCENTRATION", "RAISE_CASH")
    assert snapshot.feasible_count == 1
    assert snapshot.feasible_with_review_count == 1
    assert snapshot.rejected_count == 1
    assert snapshot.selected_alternative_id == "alt_reduce"
    assert snapshot.selected_rank == 1
    assert snapshot.top_ranked_alternative_id == "alt_reduce"
    assert snapshot.top_ranked_objective == "REDUCE_CONCENTRATION"
    assert snapshot.top_ranked_reason_codes == (
        "STATUS_FEASIBLE",
        "LOWER_TURNOVER_TIEBREAKER",
    )
    assert snapshot.rejected_reason_codes == ("ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE",)
    assert snapshot.latency_ms == 321.0


def test_extract_live_proposal_alternatives_snapshot_requires_payload() -> None:
    with pytest.raises(ValueError, match="proposal_alternatives missing"):
        extract_live_proposal_alternatives_snapshot(
            {},
            path_name="alternatives_path",
            latency_ms=10.0,
        )


def test_assert_workspace_flow_proves_rationale_replacement_lineage(monkeypatch) -> None:
    workspace_id = "aws_live_workspace"
    workspace_version_id = "awv_live_version"
    proposal_id = "ap_live_proposal"
    first_run_id = "packrun_workspace_rationale_req_001"
    replacement_run_id = "packrun_workspace_rationale_req_002"
    posts: list[tuple[str, dict[str, Any]]] = []

    def _fake_post_json(client, *, url, expected_status, json_body, headers=None):  # noqa: ANN001
        assert expected_status in {200, 201}
        posts.append((url, json_body))
        if url.endswith("/advisory/workspaces"):
            return {
                "workspace": {
                    "workspace_id": workspace_id,
                    "resolved_context": {"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
                }
            }
        if url.endswith(f"/advisory/workspaces/{workspace_id}/evaluate"):
            return {
                "latest_proposal_result": {
                    "explanation": {
                        "authority_resolution": {
                            "simulation_authority": "lotus_core",
                            "risk_authority": "lotus_risk",
                            "degraded": False,
                        }
                    }
                }
            }
        if url.endswith(f"/advisory/workspaces/{workspace_id}/save"):
            return {
                "saved_version": {
                    "workspace_version_id": workspace_version_id,
                    "replay_evidence": {"risk_lens": {"source_service": "lotus-risk"}},
                }
            }
        if url.endswith(f"/advisory/workspaces/{workspace_id}/handoff"):
            return {
                "handoff_action": "CREATED_PROPOSAL",
                "proposal": {
                    "proposal": {"proposal_id": proposal_id},
                    "version": {
                        "version_no": 1,
                        "proposal_result": {
                            "explanation": {
                                "authority_resolution": {
                                    "simulation_authority": "lotus_core",
                                    "risk_authority": "lotus_risk",
                                    "degraded": False,
                                }
                            }
                        },
                    },
                },
            }
        if url.endswith(f"/advisory/workspaces/{workspace_id}/assistant/rationale"):
            instruction = json_body["instruction"]
            current_run_id = (
                first_run_id
                if instruction == "Summarize the evaluated workspace rationale for review."
                else replacement_run_id
            )
            return {
                "generated_by": "lotus-ai",
                "assistant_output": "Evidence grounded rationale.",
                "evidence": {"workspace_id": workspace_id, "proposal_status": "READY"},
                "workflow_pack_run": {
                    "run_id": current_run_id,
                    "runtime_state": "COMPLETED",
                    "review_state": "AWAITING_REVIEW",
                    "supportability_status": "ACTION_REQUIRED",
                    "workflow_authority_owner": "lotus-advise",
                    "allowed_review_actions": ["ACCEPT", "REJECT", "REVISE", "SUPERSEDE"],
                },
            }
        if url.endswith(f"/advisory/workspaces/{workspace_id}/assistant/rationale/review-actions"):
            return {
                "workflow_pack_run": {
                    "run_id": first_run_id,
                    "runtime_state": "COMPLETED",
                    "review_state": "SUPERSEDED",
                    "supportability_status": "HISTORICAL",
                    "workflow_authority_owner": "lotus-advise",
                    "allowed_review_actions": [],
                    "superseded": True,
                    "replacement_run_id": replacement_run_id,
                },
                "summary": ["Run superseded in favor of replacement lineage."],
            }
        raise AssertionError(f"unexpected POST url: {url}")

    def _fake_request_json(
        client,
        *,
        method,
        url,
        expected_status,
        json_body=None,
        headers=None,  # noqa: ANN001
    ):
        assert method == "GET"
        assert expected_status == 200
        if url.endswith(
            f"/advisory/workspaces/{workspace_id}/saved-versions/"
            f"{workspace_version_id}/replay-evidence"
        ):
            return {
                "evidence": {"risk_lens": {"source_service": "lotus-risk"}},
                "subject": {"proposal_id": proposal_id},
                "continuity": {},
                "hashes": {"evaluation_request_hash": "hash_live"},
            }
        if url.endswith(f"/advisory/proposals/{proposal_id}/versions/1/replay-evidence"):
            return {
                "evidence": {"risk_lens": {"source_service": "lotus-risk"}},
                "subject": {"proposal_version_no": 1},
                "continuity": {"workspace_version_id": workspace_version_id},
                "hashes": {"evaluation_request_hash": "hash_live"},
            }
        raise AssertionError(f"unexpected GET url: {url}")

    monkeypatch.setattr(
        "scripts.validate_cross_service_parity_live._post_json",
        _fake_post_json,
    )
    monkeypatch.setattr(
        "scripts.validate_cross_service_parity_live._request_json",
        _fake_request_json,
    )

    result = _assert_workspace_flow(
        object(),
        advise_base_url="http://advise.dev.lotus",
        scenario=PortfolioParityScenario(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date="2026-03-25",
            reporting_currency="USD",
            issuer_coverage_status="complete",
            risk_available=True,
        ),
    )

    assert result == (
        first_run_id,
        replacement_run_id,
        "SUPERSEDED",
        "HISTORICAL",
    )
    assert posts[-1][1]["replacement_run_id"] == replacement_run_id
