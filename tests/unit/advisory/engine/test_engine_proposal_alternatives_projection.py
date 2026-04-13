from decimal import Decimal

from src.core.advisory.alternatives_models import ProposalAlternative, RejectedAlternativeCandidate
from src.core.advisory.alternatives_projection import (
    _allocation_bucket_weight,
    _build_comparison_summary,
    _build_envelope_refs,
    _build_strategy_inputs,
    _cash_balance_amount,
    _comparator_inputs,
    _primary_tradeoff,
    _rank_alternatives,
    _ranking_reason_codes,
    _top_position_weight,
    build_proposal_alternatives,
)
from src.core.advisory.alternatives_strategies import AlternativeCandidateSeed
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import (
    Money,
    ProposalAllocationBucket,
    ProposalAllocationView,
    ProposalSimulateRequest,
)


def _request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "pf_projection",
                "base_currency": "USD",
                "positions": [
                    {"instrument_id": "AAPL", "quantity": "100"},
                    {"instrument_id": "SAP", "quantity": "80"},
                    {"instrument_id": "MSFT", "quantity": "50"},
                ],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {"instrument_id": "AAPL", "price": "150", "currency": "USD"},
                    {"instrument_id": "SAP", "price": "120", "currency": "EUR"},
                    {"instrument_id": "MSFT", "price": "100", "currency": "USD"},
                    {"instrument_id": "NVDA", "price": "50", "currency": "USD"},
                ],
                "fx_rates": [{"pair": "EUR/USD", "rate": "1.1"}],
            },
            "shelf_entries": [
                {"instrument_id": "AAPL", "status": "APPROVED"},
                {"instrument_id": "SAP", "status": "APPROVED"},
                {"instrument_id": "MSFT", "status": "APPROVED"},
                {"instrument_id": "NVDA", "status": "APPROVED"},
            ],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [{"side": "BUY", "instrument_id": "NVDA", "quantity": "20"}],
            "alternatives_request": {
                "enabled": True,
                "objectives": [
                    "LOWER_TURNOVER",
                    "REDUCE_CONCENTRATION",
                    "IMPROVE_CURRENCY_ALIGNMENT",
                ],
                "include_rejected_candidates": True,
            },
        }
    )


def _baseline_result(request: ProposalSimulateRequest):
    result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash="sha256:baseline",
        idempotency_key=None,
        correlation_id="corr-baseline",
        simulation_contract_version="advisory-simulation.v1",
        policy_context=None,
    )
    result.explanation["authority_resolution"] = {
        "simulation_authority": "lotus_core",
        "risk_authority": "lotus_risk",
        "degraded": False,
        "degraded_reasons": [],
    }
    result.proposal_decision_summary = ProposalDecisionSummary(
        decision_status="READY_FOR_CLIENT_REVIEW",
        top_level_status=result.status,
        primary_reason_code="PROPOSAL_READY_FOR_CLIENT_REVIEW",
        primary_summary="Baseline proposal is ready for client review.",
        recommended_next_action="COMPARE_ALTERNATIVES",
        decision_policy_version="advisory-decision-summary.v1",
        confidence="HIGH",
        approval_requirements=[],
        material_changes=[],
        missing_evidence=[],
        advisor_action_items=[],
        evidence_refs=["proposal.explanation.authority_resolution"],
    )
    return result


def test_build_proposal_alternatives_ranks_ready_before_review_and_builds_comparison():
    request = _request()
    baseline_result = _baseline_result(request)

    def _fake_evaluator(**kwargs):
        candidate_request = kwargs["request"]
        result = run_proposal_simulation(
            portfolio=candidate_request.portfolio_snapshot,
            market_data=candidate_request.market_data_snapshot,
            shelf=candidate_request.shelf_entries,
            options=candidate_request.options,
            proposed_cash_flows=candidate_request.proposed_cash_flows,
            proposed_trades=candidate_request.proposed_trades,
            reference_model=candidate_request.reference_model,
            request_hash=kwargs["request_hash"],
            idempotency_key=kwargs["idempotency_key"],
            correlation_id=kwargs["correlation_id"],
            simulation_contract_version="advisory-simulation.v1",
            policy_context=kwargs.get("policy_context"),
        )
        result.explanation["authority_resolution"] = {
            "simulation_authority": "lotus_core",
            "risk_authority": "lotus_risk",
            "degraded": False,
            "degraded_reasons": [],
        }
        is_ready = any(trade.instrument_id == "NVDA" for trade in candidate_request.proposed_trades)
        if not is_ready:
            result.status = "PENDING_REVIEW"
        result.proposal_decision_summary = ProposalDecisionSummary(
            decision_status=("READY_FOR_CLIENT_REVIEW" if is_ready else "REQUIRES_RISK_REVIEW"),
            top_level_status=result.status,
            primary_reason_code="ALT_REASON",
            primary_summary=(
                "Alternative is ready for client review."
                if is_ready
                else "Alternative requires risk review before recommendation."
            ),
            recommended_next_action="COMPARE_ALTERNATIVES" if is_ready else "REVIEW_RISK",
            decision_policy_version="advisory-decision-summary.v1",
            confidence="HIGH" if is_ready else "MEDIUM",
            approval_requirements=[],
            material_changes=[],
            missing_evidence=[],
            advisor_action_items=[],
            evidence_refs=["proposal.explanation.authority_resolution"],
        )
        return result

    projection = build_proposal_alternatives(
        request=request,
        baseline_result=baseline_result,
        correlation_id="corr-projection",
        evaluator=_fake_evaluator,
    )

    assert projection is not None
    assert [item.rank for item in projection.alternatives] == [1, 2, 3]
    assert projection.alternatives[0].objective == "LOWER_TURNOVER"
    assert projection.alternatives[0].comparison_summary is not None
    assert projection.alternatives[0].ranking_projection is not None
    assert "STATUS_FEASIBLE" in projection.alternatives[0].ranking_projection.ranking_reason_codes


def test_build_proposal_alternatives_returns_none_without_request() -> None:
    request = _request()
    request.alternatives_request = None

    projection = build_proposal_alternatives(
        request=request,
        baseline_result=_baseline_result(request),
        correlation_id="corr-none",
    )

    assert projection is None


def test_build_proposal_alternatives_selection_mode_marks_only_ranked_selection() -> None:
    request = _request()
    request.alternatives_request.selected_alternative_id = "alt_lower_turnover_pf_projection_nvda"
    projection = build_proposal_alternatives(
        request=request,
        baseline_result=_baseline_result(request),
        correlation_id="corr-selection",
        evaluator=lambda **kwargs: _baseline_result(kwargs["request"]),
    )

    assert projection is not None
    assert projection.selected_alternative_id == "alt_lower_turnover_pf_projection_nvda"
    assert projection.alternatives[0].selected is True
    assert all(item.selected is False for item in projection.alternatives[1:])


def test_build_strategy_inputs_preserves_missing_prices_and_notional_trades() -> None:
    payload = _request().model_dump(mode="json")
    payload["market_data_snapshot"]["prices"] = payload["market_data_snapshot"]["prices"][:1]
    payload["proposed_trades"] = [
        {
            "side": "BUY",
            "instrument_id": "NVDA",
            "notional": {"amount": "2500", "currency": "USD"},
        }
    ]
    request = ProposalSimulateRequest.model_validate(payload)

    strategy_inputs = _build_strategy_inputs(request)

    assert strategy_inputs.positions[1].price is None
    assert strategy_inputs.positions[1].currency is None
    assert strategy_inputs.current_proposed_trades[0].notional_amount == Decimal("2500")
    assert strategy_inputs.current_proposed_trades[0].notional_currency == "USD"


def test_projection_helpers_cover_rejected_status_and_comparison_fallbacks() -> None:
    baseline_result = _baseline_result(_request())
    baseline_result.explanation["risk_lens"] = {
        "single_position_concentration": {"top_position_weight_proposed": "0.20"}
    }
    baseline_result.after_simulated.cash_balances = [Money(currency="USD", amount="1000")]
    baseline_result.after_simulated.allocation_views = [
        ProposalAllocationView(
            dimension="currency",
            total_value=Money(currency="USD", amount="1000"),
            buckets=[
                ProposalAllocationBucket(
                    key="USD",
                    weight="0.65",
                    value=Money(currency="USD", amount="650"),
                    position_count=2,
                )
            ],
        )
    ]
    alternative = ProposalAlternative(
        alternative_id="alt_blocked",
        label="Blocked alternative",
        objective="REDUCE_CONCENTRATION",
        status="REJECTED_POLICY_BLOCKED",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        intents=[
            {"intent_type": "SECURITY_TRADE", "side": "SELL", "instrument_id": "AAPL"},
            {"intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "MSFT"},
        ],
        proposal_decision_summary={
            "decision_status": "BLOCKED_REMEDIATION_REQUIRED",
            "top_level_status": "BLOCKED",
            "approval_requirements": [{"approval_type": "RISK", "blocking_until_approved": True}],
            "missing_evidence": [{"reason_code": "MISSING_RISK_LENS"}],
        },
        evidence_refs=["evidence://proposal-alternatives/alt_blocked/simulation"],
    )

    blocked_inputs = _comparator_inputs(alternative=alternative, objective_rank=9)
    assert blocked_inputs["status_priority"] == 2
    assert "APPROVALS_INCREASE_REVIEW_POSTURE" in _ranking_reason_codes(alternative=alternative)
    assert "MISSING_EVIDENCE_LOWERS_RANK" in _ranking_reason_codes(alternative=alternative)
    assert "LOWER_TURNOVER_TIEBREAKER" not in _ranking_reason_codes(alternative=alternative)
    assert alternative.rank is None
    assert _top_position_weight({}, "top_position_weight_proposed") is None
    assert _cash_balance_amount([], "USD") == Decimal("0")
    assert _allocation_bucket_weight([], "currency", "USD") is None
    assert (
        _top_position_weight(
            {"single_position_concentration": "invalid"},
            "top_position_weight_proposed",
        )
        is None
    )
    assert _allocation_bucket_weight(
        baseline_result.after_simulated.allocation_views,
        "currency",
        "USD",
    ) == Decimal("0.65")


def test_projection_helper_functions_build_refs_and_risk_values() -> None:
    alternative = ProposalAlternative(
        alternative_id="alt_ready",
        label="Ready alternative",
        objective="LOWER_TURNOVER",
        status="FEASIBLE",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        intents=[{"intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "NVDA"}],
        proposal_decision_summary={"decision_status": "READY_FOR_CLIENT_REVIEW"},
        evidence_refs=["evidence://one", "evidence://two"],
    )
    refs = _build_envelope_refs(
        [alternative],
        [
            RejectedAlternativeCandidate(
                candidate_id="alt_seed",
                objective="REDUCE_CONCENTRATION",
                status="REJECTED_CONSTRAINT_VIOLATION",
                reason_code="LIMIT",
                summary="limit",
                evidence_refs=["evidence://three"],
            )
        ],
    )

    assert refs == ["evidence://one", "evidence://three", "evidence://two"]
    assert _top_position_weight(
        {"single_position_concentration": {"top_position_weight_proposed": "0.12"}},
        "top_position_weight_proposed",
    ) == Decimal("0.12")


def test_rank_alternatives_leaves_rejected_selection_unranked() -> None:
    baseline_result = _baseline_result(_request())
    blocked = ProposalAlternative(
        alternative_id="alt_blocked",
        label="Blocked",
        objective="REDUCE_CONCENTRATION",
        status="REJECTED_POLICY_BLOCKED",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        intents=[],
        proposal_decision_summary={
            "decision_status": "BLOCKED_REMEDIATION_REQUIRED",
            "top_level_status": "BLOCKED",
        },
    )

    ranked = _rank_alternatives(
        baseline_result=baseline_result,
        alternatives=[blocked],
        candidate_seeds=(
            AlternativeCandidateSeed(
                candidate_id="alt_blocked",
                objective="REDUCE_CONCENTRATION",
                strategy_id="reduce_concentration_v1",
                label="Blocked",
                summary="Blocked",
            ),
        ),
        selected_alternative_id="alt_blocked",
    )

    assert ranked[0].rank is None
    assert ranked[0].selected is False
    assert ranked[0].ranking_projection is not None


def test_build_comparison_summary_records_improvements_and_deteriorations() -> None:
    request = _request()
    baseline_result = _baseline_result(request)
    baseline_result.proposal_decision_summary.approval_requirements = [
        {"approval_type": "RISK", "blocking_until_approved": True}
    ]
    baseline_result.proposal_decision_summary.missing_evidence = [{"reason_code": "MISSING"}]
    baseline_result.explanation["risk_lens"] = {
        "single_position_concentration": {"top_position_weight_proposed": "0.30"}
    }
    baseline_result.after_simulated.cash_balances = [Money(currency="USD", amount="1000")]

    improved = ProposalAlternative(
        alternative_id="alt_improved",
        label="Improved",
        objective="REDUCE_CONCENTRATION",
        status="FEASIBLE",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        intents=[{"intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "NVDA"}],
        proposal_decision_summary={
            "decision_status": "READY_FOR_CLIENT_REVIEW",
            "top_level_status": baseline_result.status,
            "approval_requirements": [],
            "missing_evidence": [],
            "risk_posture": {
                "single_position_concentration": {"top_position_weight_proposed": "0.10"}
            },
        },
    )
    improved_summary = _build_comparison_summary(
        baseline_result=baseline_result,
        alternative=improved,
    )
    assert "Approval burden is lower than the baseline proposal." in improved_summary.improvements
    assert (
        "Evidence completeness is stronger than the baseline proposal."
        in improved_summary.improvements
    )
    assert (
        "Single-name concentration is lower than the baseline proposal."
        in improved_summary.improvements
    )
    assert _primary_tradeoff(alternative=improved) == (
        "Alternative is feasible without additional review posture."
    )

    deteriorated = ProposalAlternative(
        alternative_id="alt_deteriorated",
        label="Deteriorated",
        objective="LOWER_TURNOVER",
        status="FEASIBLE_WITH_REVIEW",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        intents=[{"intent_type": "SECURITY_TRADE", "side": "SELL", "instrument_id": "AAPL"}],
        proposal_decision_summary={
            "decision_status": "REQUIRES_RISK_REVIEW",
            "top_level_status": "PENDING_REVIEW",
            "approval_requirements": [
                {"approval_type": "RISK", "blocking_until_approved": True},
                {"approval_type": "COMPLIANCE", "blocking_until_approved": False},
            ],
            "missing_evidence": [{"reason_code": "MISSING"}, {"reason_code": "SECOND"}],
            "risk_posture": {
                "single_position_concentration": {"top_position_weight_proposed": "0.40"}
            },
        },
    )
    deteriorated_summary = _build_comparison_summary(
        baseline_result=baseline_result,
        alternative=deteriorated,
    )
    assert (
        "Approval burden is higher than the baseline proposal."
        in deteriorated_summary.deteriorations
    )
    assert (
        "Evidence completeness is weaker than the baseline proposal."
        in deteriorated_summary.deteriorations
    )
    assert (
        "Single-name concentration is higher than the baseline proposal."
        in deteriorated_summary.deteriorations
    )
    assert _primary_tradeoff(alternative=deteriorated) == (
        "Alternative remains feasible but requires additional review posture."
    )

    blocked = ProposalAlternative(
        alternative_id="alt_rejected",
        label="Rejected",
        objective="RAISE_CASH",
        status="REJECTED_POLICY_BLOCKED",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        intents=[{"intent_type": "SECURITY_TRADE", "side": "SELL", "instrument_id": "AAPL"}],
        proposal_decision_summary={"decision_status": "BLOCKED_REMEDIATION_REQUIRED"},
    )
    assert _primary_tradeoff(alternative=blocked) == (
        "Alternative is not ranked because policy posture does not support recommendation."
    )
