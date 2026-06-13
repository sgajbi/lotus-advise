from datetime import datetime, timezone
from typing import cast

from src.core.advisory.alternatives_models import ProposalAlternatives
from src.core.advisory.artifact_assumption_models import (
    ProposalArtifactAssumptionsAndLimits,
    ProposalArtifactDisclosures,
    ProposalArtifactInclusionFlag,
    ProposalArtifactPricingAssumptions,
    ProposalArtifactProductDoc,
)
from src.core.advisory.artifact_evidence import (
    build_artifact_evidence_bundle,
    finalize_artifact_evidence_hashes,
)
from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.artifact_portfolio import (
    build_portfolio_state_payload,
    largest_weight_changes,
)
from src.core.advisory.artifact_portfolio_models import (
    ProposalArtifactPortfolioDelta,
    ProposalArtifactPortfolioImpact,
)
from src.core.advisory.artifact_review import (
    build_risk_lens_summary,
    build_suitability_summary,
)
from src.core.advisory.artifact_summary import (
    build_takeaways,
    resolve_next_step,
    resolve_objective_tags,
)
from src.core.advisory.artifact_summary_models import (
    ProposalArtifactSummary,
)
from src.core.advisory.artifact_trades import build_trades_and_funding
from src.core.advisory.decision_summary import build_proposal_decision_summary
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.gate_models import GateDecision
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


def build_proposal_artifact(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    created_at: str | None = None,
) -> ProposalArtifact:
    artifact = ProposalArtifact(
        gate_decision=_artifact_gate_decision(request=request, result=proposal_result),
        proposal_decision_summary=_artifact_decision_summary(proposal_result),
        proposal_alternatives=_artifact_alternatives(proposal_result),
        artifact_id=proposal_result.proposal_run_id.replace("pr_", "pa_", 1),
        proposal_run_id=proposal_result.proposal_run_id,
        correlation_id=proposal_result.correlation_id,
        created_at=_artifact_created_at(created_at),
        status=proposal_result.status,
        summary=_artifact_summary(request=request, result=proposal_result),
        portfolio_impact=_artifact_portfolio_impact(
            request=request,
            result=proposal_result,
        ),
        trades_and_funding=build_trades_and_funding(request=request, result=proposal_result),
        risk_lens=build_risk_lens_summary(proposal_result),
        suitability_summary=build_suitability_summary(request=request, result=proposal_result),
        assumptions_and_limits=_artifact_assumptions(request=request, result=proposal_result),
        disclosures=_artifact_disclosures(proposal_result),
        evidence_bundle=build_artifact_evidence_bundle(
            request=request,
            proposal_result=proposal_result,
        ),
    )
    return finalize_artifact_evidence_hashes(artifact=artifact, request=request)


def _artifact_gate_decision(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> GateDecision:
    if result.gate_decision is not None:
        return result.gate_decision
    return evaluate_gate_decision(
        status=result.status,
        rule_results=result.rule_results,
        suitability=result.suitability,
        diagnostics=result.diagnostics,
        options=request.options,
        default_requires_client_consent=True,
    )


def _artifact_decision_summary(result: ProposalResult) -> ProposalDecisionSummary:
    if result.proposal_decision_summary is not None:
        return result.proposal_decision_summary
    return build_proposal_decision_summary(result)


def _artifact_alternatives(result: ProposalResult) -> ProposalAlternatives | None:
    if result.proposal_alternatives is None:
        return None
    return cast(ProposalAlternatives, result.proposal_alternatives.model_copy(deep=True))


def _artifact_created_at(created_at: str | None) -> str:
    return created_at or datetime.now(timezone.utc).isoformat()


def _artifact_summary(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactSummary:
    return ProposalArtifactSummary(
        title=f"Proposal for {request.portfolio_snapshot.portfolio_id}",
        objective_tags=resolve_objective_tags(request=request, result=result),
        advisor_notes=[],
        recommended_next_step=resolve_next_step(result),
        key_takeaways=build_takeaways(request=request, result=result),
    )


def _artifact_portfolio_impact(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactPortfolioImpact:
    before_state = result.before
    after_state = result.after_simulated
    return ProposalArtifactPortfolioImpact(
        before=build_portfolio_state_payload(before_state),
        after=build_portfolio_state_payload(after_state),
        delta=ProposalArtifactPortfolioDelta(
            total_value_delta={
                "amount": after_state.total_value.amount - before_state.total_value.amount,
                "currency": before_state.total_value.currency,
            },
            largest_weight_changes=largest_weight_changes(
                before_state,
                after_state,
                limit=request.options.drift_top_contributors_limit,
            ),
        ),
        reconciliation=(
            result.reconciliation.model_dump(mode="json")
            if result.reconciliation is not None
            else None
        ),
    )


def _artifact_assumptions(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactAssumptionsAndLimits:
    market_data_snapshot_id = result.lineage.market_data_snapshot_id
    return ProposalArtifactAssumptionsAndLimits(
        pricing=ProposalArtifactPricingAssumptions(
            market_data_snapshot_id=market_data_snapshot_id,
            prices_as_of=market_data_snapshot_id,
            fx_as_of=market_data_snapshot_id,
            valuation_mode=request.options.valuation_mode.value,
        ),
        costs_and_fees=ProposalArtifactInclusionFlag(
            included=False,
            notes="Transaction costs, fees, and bid/ask spreads are not modeled.",
        ),
        tax=ProposalArtifactInclusionFlag(
            included=False,
            notes="Tax impact is not modeled in the proposal artifact.",
        ),
        execution=ProposalArtifactInclusionFlag(
            included=False,
            notes="Execution timing and slippage are not modeled.",
        ),
    )


def _artifact_disclosures(result: ProposalResult) -> ProposalArtifactDisclosures:
    return ProposalArtifactDisclosures(
        risk_disclaimer=(
            "This proposal is based on market-data snapshots and does not guarantee "
            "future performance."
        ),
        product_docs=[
            ProposalArtifactProductDoc(
                instrument_id=instrument_id,
                doc_ref="KID/FactSheet reference pending source confirmation",
            )
            for instrument_id in _traded_instrument_ids(result)
        ],
    )


def _traded_instrument_ids(result: ProposalResult) -> list[str]:
    return sorted(
        {
            intent.instrument_id
            for intent in result.intents
            if intent.intent_type == "SECURITY_TRADE"
        }
    )
