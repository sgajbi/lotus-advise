from src.core.advisory.alternatives_projection import build_proposal_alternatives
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalSimulateRequest


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
