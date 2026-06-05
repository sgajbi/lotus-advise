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
        return _next_step_from_gate_decision(result.gate_decision)
    return _next_step_without_gate_decision(result)


def _next_step_from_gate_decision(gate_decision: object) -> str:
    gate = getattr(gate_decision, "gate", None)
    if gate == "BLOCKED":
        return _blocked_gate_next_step(gate_decision)
    return {
        "COMPLIANCE_REVIEW_REQUIRED": "COMPLIANCE_REVIEW",
        "RISK_REVIEW_REQUIRED": "RISK_REVIEW",
        "CLIENT_CONSENT_REQUIRED": "CLIENT_CONSENT",
        "EXECUTION_READY": "EXECUTION_READY",
    }.get(str(gate), "RISK_REVIEW")


def _blocked_gate_next_step(gate_decision: object) -> str:
    if _has_high_suitability_gate_reason(gate_decision):
        return "COMPLIANCE_REVIEW"
    return "RISK_REVIEW"


def _has_high_suitability_gate_reason(gate_decision: object) -> bool:
    return any(
        reason.source == "SUITABILITY" and reason.severity == "HIGH"
        for reason in getattr(gate_decision, "reasons", [])
    )


def _next_step_without_gate_decision(result: ProposalResult) -> str:
    suitability_next_step = _next_step_from_suitability(result)
    if suitability_next_step is not None:
        return suitability_next_step
    if result.status == "READY":
        return "CLIENT_CONSENT"
    return "RISK_REVIEW"


def _next_step_from_suitability(result: ProposalResult) -> str | None:
    if result.suitability is None:
        return None
    return {
        "COMPLIANCE_REVIEW": "COMPLIANCE_REVIEW",
        "RISK_REVIEW": "RISK_REVIEW",
    }.get(result.suitability.recommended_gate)


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
