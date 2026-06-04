from src.core.advisory.artifact_formatting import quantized_weight_str
from src.core.advisory.artifact_portfolio import cash_weight
from src.core.advisory.artifact_summary_models import ProposalArtifactTakeaway
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


def resolve_objective_tags(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[str]:
    tags = []
    has_cash_flow = bool(request.proposed_cash_flows)
    has_trade = any(intent.intent_type == "SECURITY_TRADE" for intent in result.intents)
    if has_trade:
        tags.append("RISK_ALIGNMENT")
    if has_cash_flow:
        tags.append("CASH_DEPLOYMENT")
    if result.drift_analysis is not None:
        if (
            result.drift_analysis.asset_class.drift_total_after
            < result.drift_analysis.asset_class.drift_total_before
        ):
            tags.append("DRIFT_REDUCTION")
    if not tags:
        tags.append("PORTFOLIO_MAINTENANCE")
    return tags


def resolve_next_step(result: ProposalResult) -> str:
    if result.gate_decision is not None:
        if result.gate_decision.gate == "BLOCKED":
            has_high_suitability = any(
                reason.source == "SUITABILITY" and reason.severity == "HIGH"
                for reason in result.gate_decision.reasons
            )
            return "COMPLIANCE_REVIEW" if has_high_suitability else "RISK_REVIEW"
        if result.gate_decision.gate == "COMPLIANCE_REVIEW_REQUIRED":
            return "COMPLIANCE_REVIEW"
        if result.gate_decision.gate == "RISK_REVIEW_REQUIRED":
            return "RISK_REVIEW"
        if result.gate_decision.gate == "CLIENT_CONSENT_REQUIRED":
            return "CLIENT_CONSENT"
        if result.gate_decision.gate == "EXECUTION_READY":
            return "EXECUTION_READY"
        return "RISK_REVIEW"
    if result.suitability is not None:
        if result.suitability.recommended_gate == "COMPLIANCE_REVIEW":
            return "COMPLIANCE_REVIEW"
        if result.suitability.recommended_gate == "RISK_REVIEW":
            return "RISK_REVIEW"
    if result.status == "READY":
        return "CLIENT_CONSENT"
    if result.status == "PENDING_REVIEW":
        return "RISK_REVIEW"
    return "RISK_REVIEW"


def build_takeaways(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[ProposalArtifactTakeaway]:
    security_trade_count = sum(1 for item in result.intents if item.intent_type == "SECURITY_TRADE")
    fx_intent_count = sum(1 for item in result.intents if item.intent_type == "FX_SPOT")
    takeaways = [
        ProposalArtifactTakeaway(
            code="STATUS",
            value=f"Proposal status is {result.status}.",
        ),
        ProposalArtifactTakeaway(
            code="INTENTS",
            value=(
                f"Generated {security_trade_count} security trades and "
                f"{fx_intent_count} FX intents."
            ),
        ),
        ProposalArtifactTakeaway(
            code="CASH",
            value=(
                f"Cash weight changed from {quantized_weight_str(cash_weight(result.before))} "
                f"to {quantized_weight_str(cash_weight(result.after_simulated))}."
            ),
        ),
    ]
    if result.drift_analysis is not None:
        drift_before = quantized_weight_str(result.drift_analysis.asset_class.drift_total_before)
        drift_after = quantized_weight_str(result.drift_analysis.asset_class.drift_total_after)
        takeaways.append(
            ProposalArtifactTakeaway(
                code="DRIFT",
                value=f"Asset-class drift changed from {drift_before} to {drift_after}.",
            )
        )
    if request.options.enable_suitability_scanner and result.suitability is not None:
        takeaways.append(
            ProposalArtifactTakeaway(
                code="SUITABILITY",
                value=(
                    f"Suitability issues: new={result.suitability.summary.new_count}, "
                    f"resolved={result.suitability.summary.resolved_count}, "
                    f"persistent={result.suitability.summary.persistent_count}."
                ),
            )
        )
    return takeaways
