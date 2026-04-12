from copy import deepcopy

import pytest

from src.core.advisory import (
    AlternativeCandidateSeed,
    ProposalAlternativesRequest,
    normalize_alternatives_request,
)
from src.core.advisory.alternatives_enrichment import (
    build_alternative_simulate_request,
    evaluate_alternative_candidates_batch,
)
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalResult, ProposalSimulateRequest


def _base_request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "pf_alt",
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
            "proposed_cash_flows": [
                {"intent_type": "CASH_FLOW", "currency": "USD", "amount": "10"}
            ],
            "proposed_trades": [
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_OLD",
                    "quantity": "1",
                }
            ],
        }
    )


def _normalized_request(max_alternatives: int = 3):
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=["REDUCE_CONCENTRATION"],
            max_alternatives=max_alternatives,
        )
    )
    assert normalized is not None
    return normalized


def _candidate(
    candidate_id: str,
    *,
    label: str = "Reduce concentration",
    generated_intents: list[dict[str, str]] | None = None,
) -> AlternativeCandidateSeed:
    candidate_intents = (
        generated_intents
        if generated_intents is not None
        else [
            {
                "intent_type": "SECURITY_TRADE",
                "side": "SELL",
                "instrument_id": "EQ_OLD",
                "quantity": "2",
            },
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_NEW",
                "quantity": "4",
            },
        ]
    )
    return AlternativeCandidateSeed(
        candidate_id=candidate_id,
        objective="REDUCE_CONCENTRATION",
        strategy_id="reduce_concentration_v1",
        status="READY_FOR_SIMULATION",
        label=label,
        summary="Sell existing risk and redeploy into a smaller position.",
        generated_intents=candidate_intents,
    )


def _proposal_result(
    request: ProposalSimulateRequest,
    *,
    status: str = "READY",
    simulation_authority: str = "lotus_core",
    risk_authority: str = "lotus_risk",
) -> ProposalResult:
    result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash="sha256:test",
        idempotency_key=None,
        correlation_id="corr-alt-test",
        simulation_contract_version="advisory-simulation.v1",
        policy_context=None,
    )
    result.status = status
    explanation = dict(result.explanation)
    explanation["authority_resolution"] = {
        "simulation_authority": simulation_authority,
        "risk_authority": risk_authority,
        "degraded": simulation_authority != "lotus_core" or risk_authority != "lotus_risk",
        "degraded_reasons": [],
    }
    explanation["risk_lens"] = {"source_service": "lotus-risk"}
    result.explanation = explanation
    result.proposal_decision_summary = ProposalDecisionSummary(
        decision_status="READY_FOR_CLIENT_REVIEW",
        top_level_status=status,
        primary_reason_code="READY_FOR_ADVISOR_REVIEW",
        primary_summary="Alternative is ready for advisor review.",
        recommended_next_action="COMPARE_ALTERNATIVES",
        decision_policy_version="advisory-decision-summary.v1",
        confidence="HIGH",
        approval_requirements=[],
        material_changes=[],
        missing_evidence=[],
        advisor_action_items=[],
        evidence_refs=["proposal.explanation.authority_resolution"],
    )
    return ProposalResult.model_validate(result.model_dump(mode="json"))


def test_build_alternative_simulate_request_replaces_baseline_intents():
    request = _base_request()
    candidate = _candidate("alt_replace")

    alternative_request = build_alternative_simulate_request(
        base_request=request,
        candidate=candidate,
    )

    assert [trade.instrument_id for trade in alternative_request.proposed_trades] == [
        "EQ_OLD",
        "EQ_NEW",
    ]
    assert alternative_request.proposed_cash_flows == []
    assert [trade.instrument_id for trade in request.proposed_trades] == ["EQ_OLD"]
    assert len(request.proposed_cash_flows) == 1


def test_evaluate_alternative_candidates_batch_deduplicates_identical_payloads(monkeypatch):
    request = _base_request()
    normalized = _normalized_request()
    calls: list[ProposalSimulateRequest] = []

    def _fake_evaluate(**kwargs):
        candidate_request = kwargs["request"]
        calls.append(candidate_request)
        return _proposal_result(candidate_request)

    monkeypatch.setattr(
        "src.core.advisory.alternatives_enrichment.evaluate_advisory_proposal",
        _fake_evaluate,
    )

    first_candidate = _candidate("alt_1", label="Path 1")
    second_candidate = _candidate("alt_2", label="Path 2")
    evaluation = evaluate_alternative_candidates_batch(
        base_request=request,
        normalized_request=normalized,
        candidates=[first_candidate, second_candidate],
        correlation_id="corr-batch",
    )

    assert len(calls) == 1
    assert len(evaluation.alternatives) == 2
    assert len(evaluation.simulation_records) == 2
    assert evaluation.alternatives[0].alternative_id == "alt_1"
    assert evaluation.alternatives[1].alternative_id == "alt_2"
    assert evaluation.alternatives[0].simulation_result_ref == (
        "evidence://proposal-alternatives/alt_1/simulation"
    )
    assert evaluation.alternatives[1].risk_lens_ref == (
        "evidence://proposal-alternatives/alt_2/risk"
    )
    assert all(
        item.proposal_decision_summary["primary_reason_code"] == "READY_FOR_ADVISOR_REVIEW"
        for item in evaluation.alternatives
    )


@pytest.mark.parametrize(
    ("simulation_authority", "risk_authority", "expected_status", "expected_reason_code"),
    [
        (
            "lotus_advise_local_fallback",
            "lotus_risk",
            "REJECTED_SIMULATION_FAILED",
            "LOTUS_CORE_SIMULATION_UNAVAILABLE",
        ),
        (
            "lotus_core",
            "unavailable",
            "REJECTED_RISK_EVIDENCE_UNAVAILABLE",
            "LOTUS_RISK_ENRICHMENT_UNAVAILABLE",
        ),
    ],
)
def test_evaluate_alternative_candidates_batch_rejects_degraded_authority(
    monkeypatch,
    simulation_authority: str,
    risk_authority: str,
    expected_status: str,
    expected_reason_code: str,
):
    request = _base_request()
    normalized = _normalized_request()

    def _fake_evaluate(**kwargs):
        return _proposal_result(
            kwargs["request"],
            simulation_authority=simulation_authority,
            risk_authority=risk_authority,
        )

    monkeypatch.setattr(
        "src.core.advisory.alternatives_enrichment.evaluate_advisory_proposal",
        _fake_evaluate,
    )

    evaluation = evaluate_alternative_candidates_batch(
        base_request=request,
        normalized_request=normalized,
        candidates=[_candidate("alt_reject")],
        correlation_id="corr-degraded",
    )

    assert evaluation.alternatives == []
    assert len(evaluation.rejected_candidates) == 1
    rejected = evaluation.rejected_candidates[0]
    assert rejected.status == expected_status
    assert rejected.reason_code == expected_reason_code


def test_evaluate_alternative_candidates_batch_rejects_overflow_without_upstream_calls(monkeypatch):
    request = _base_request()
    normalized = _normalized_request(max_alternatives=1)
    called = False

    def _fake_evaluate(**kwargs):
        nonlocal called
        called = True
        return _proposal_result(kwargs["request"])

    monkeypatch.setattr(
        "src.core.advisory.alternatives_enrichment.evaluate_advisory_proposal",
        _fake_evaluate,
    )

    evaluation = evaluate_alternative_candidates_batch(
        base_request=request,
        normalized_request=normalized,
        candidates=[_candidate("alt_keep"), _candidate("alt_overflow")],
        correlation_id="corr-overflow",
    )

    assert called is True
    assert len(evaluation.alternatives) == 1
    assert len(evaluation.rejected_candidates) == 1
    assert evaluation.rejected_candidates[0].reason_code == "ALTERNATIVE_CANDIDATE_LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    ("generated_intents", "expected_reason_code"),
    [
        ([], "ALTERNATIVE_CANDIDATE_HAS_NO_INTENTS"),
        (
            [{"intent_type": "FX_SWAP", "currency": "USD", "amount": "1"}],
            "ALTERNATIVE_INTENT_UNSUPPORTED",
        ),
    ],
)
def test_evaluate_alternative_candidates_batch_rejects_invalid_candidate_intents(
    monkeypatch,
    generated_intents: list[dict[str, str]],
    expected_reason_code: str,
):
    request = _base_request()
    normalized = _normalized_request()

    monkeypatch.setattr(
        "src.core.advisory.alternatives_enrichment.evaluate_advisory_proposal",
        lambda **kwargs: pytest.fail("upstream evaluation should not be called"),
    )

    evaluation = evaluate_alternative_candidates_batch(
        base_request=request,
        normalized_request=normalized,
        candidates=[_candidate("alt_invalid", generated_intents=deepcopy(generated_intents))],
        correlation_id="corr-invalid",
    )

    assert evaluation.alternatives == []
    assert len(evaluation.rejected_candidates) == 1
    assert evaluation.rejected_candidates[0].reason_code == expected_reason_code
