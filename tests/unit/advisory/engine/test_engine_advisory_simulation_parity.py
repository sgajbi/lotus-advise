from typing import Any

import pytest

from src.core.advisory.source_effects import (
    build_advise_owned_proposal_result_from_source_effects,
    extract_core_decision_compatibility_snapshot,
    map_core_payload_to_projected_transaction_effects,
)
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult
from tests.shared.advisory_simulation_parity import (
    iter_parity_scenarios,
    normalize_result_for_parity,
)


@pytest.mark.parametrize(
    ("scenario_name", "request_hash", "payload", "expected"),
    [
        (
            scenario["name"],
            scenario["request_hash"],
            scenario["payload"],
            scenario["expected"],
        )
        for scenario in iter_parity_scenarios()
    ],
    ids=[scenario["name"] for scenario in iter_parity_scenarios()],
)
def test_local_advisory_engine_matches_curated_parity_scenarios(
    scenario_name: str,
    request_hash: str,
    payload: dict,
    expected: dict,
) -> None:
    request = ProposalSimulateRequest.model_validate(payload)

    result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        simulation_contract_version="advisory-simulation.v1",
    )

    assert normalize_result_for_parity(result) == expected, scenario_name


@pytest.mark.parametrize(
    ("scenario_name", "request_hash", "payload", "expected"),
    [
        (
            scenario["name"],
            scenario["request_hash"],
            scenario["payload"],
            scenario["expected"],
        )
        for scenario in iter_parity_scenarios()
    ],
    ids=[f"{scenario['name']}_core_v1_dual_run" for scenario in iter_parity_scenarios()],
)
def test_core_v1_decision_parity_uses_advise_owned_output_for_curated_scenarios(
    scenario_name: str,
    request_hash: str,
    payload: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    result = _replay_advise_decisions_from_stale_core_v1_payload(
        payload=payload,
        request_hash=request_hash,
    )

    assert normalize_result_for_parity(result) == expected, scenario_name
    _assert_stale_core_decision_parity(result)


def test_core_v1_decision_parity_uses_advise_owned_output_for_private_banking_case() -> None:
    payload = ProposalSimulateRequest.model_config["json_schema_extra"]["example"]

    result = _replay_advise_decisions_from_stale_core_v1_payload(
        payload=payload,
        request_hash="proposal_hash_pb_sg_global_bal_001",
    )

    assert result.status == "READY"
    assert result.lineage.request_hash == "proposal_hash_pb_sg_global_bal_001"
    assert result.allocation_lens.source == "LOTUS_CORE"
    assert result.explanation["core_projected_transaction_effects"][
        "source_effects_hash"
    ].startswith("sha256:")
    _assert_stale_core_decision_parity(result)


def _replay_advise_decisions_from_stale_core_v1_payload(
    *,
    payload: dict[str, Any],
    request_hash: str,
) -> ProposalResult:
    request = ProposalSimulateRequest.model_validate(payload)
    core_projection = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        simulation_contract_version="advisory-simulation.v1",
    )
    core_v1_payload = _stale_core_v1_decision_payload(core_projection)

    return build_advise_owned_proposal_result_from_source_effects(
        request=request,
        source_effects=map_core_payload_to_projected_transaction_effects(core_v1_payload),
        compatibility_snapshot=extract_core_decision_compatibility_snapshot(core_v1_payload),
        policy_context=None,
    )


def _stale_core_v1_decision_payload(result: ProposalResult) -> dict[str, Any]:
    payload = result.model_dump(mode="json")
    payload["status"] = "READY" if result.status != "READY" else "BLOCKED"
    payload["suitability"] = {
        "summary": {
            "new_count": 99,
            "resolved_count": 0,
            "persistent_count": 99,
            "highest_severity_new": "HIGH",
        },
        "issues": [],
        "policy_pack_id": "legacy-core-v1-compatibility",
        "policy_version": "legacy-core-advisory-decision.v1",
        "recommended_gate": _stale_recommended_gate(result),
    }
    payload["gate_decision"] = _stale_core_gate_decision(result)
    return payload


def _stale_recommended_gate(result: ProposalResult) -> str:
    if result.suitability is not None and result.suitability.recommended_gate != "NONE":
        return "NONE"
    return "COMPLIANCE_REVIEW"


def _stale_core_gate_decision(result: ProposalResult) -> dict[str, Any]:
    stale_gate = "BLOCKED"
    stale_next_step = "FIX_INPUT"
    if result.gate_decision is not None and result.gate_decision.gate == stale_gate:
        stale_gate = "COMPLIANCE_REVIEW_REQUIRED"
        stale_next_step = "COMPLIANCE_REVIEW"
    return {
        "gate": stale_gate,
        "recommended_next_step": stale_next_step,
        "reasons": [
            {
                "reason_code": "LEGACY_CORE_V1_DECISION",
                "severity": "HIGH",
                "source": "CORE_COMPATIBILITY",
                "details": {},
            }
        ],
        "summary": {
            "hard_fail_count": 1,
            "soft_fail_count": 0,
            "new_high_suitability_count": 99,
            "new_medium_suitability_count": 0,
        },
    }


def _assert_stale_core_decision_parity(result: ProposalResult) -> None:
    core_decisions = result.explanation["non_authoritative_core_decisions"]
    parity = result.explanation["core_decision_parity"]

    assert core_decisions["reported_status"] != result.status
    assert core_decisions["suitability"]["policy_pack_id"] == "legacy-core-v1-compatibility"
    assert parity["status"] == "MISMATCH"
    assert parity["core_decisions_authoritative"] is False
    assert {
        "status",
        "suitability.summary.new_count",
        "suitability.summary.persistent_count",
        "suitability.recommended_gate",
        "gate_decision.gate",
        "gate_decision.recommended_next_step",
    }.issubset(set(parity["compared_fields"]))
