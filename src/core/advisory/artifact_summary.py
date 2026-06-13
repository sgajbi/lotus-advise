from src.core.advisory.artifact_formatting import quantized_weight_str
from src.core.advisory.artifact_portfolio import cash_weight
from src.core.advisory.artifact_summary_models import ProposalArtifactTakeaway
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


def resolve_objective_tags(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[str]:
    tags = _resolved_objective_tags(request=request, result=result)
    if tags:
        return tags
    return ["PORTFOLIO_MAINTENANCE"]


def _resolved_objective_tags(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[str]:
    tags = []
    if _has_security_trade(result):
        tags.append("RISK_ALIGNMENT")
    if request.proposed_cash_flows:
        tags.append("CASH_DEPLOYMENT")
    if _reduces_asset_class_drift(result):
        tags.append("DRIFT_REDUCTION")
    return tags


def _has_security_trade(result: ProposalResult) -> bool:
    return any(intent.intent_type == "SECURITY_TRADE" for intent in result.intents)


def _reduces_asset_class_drift(result: ProposalResult) -> bool:
    if result.drift_analysis is None:
        return False
    asset_class_drift = result.drift_analysis.asset_class
    return bool(asset_class_drift.drift_total_after < asset_class_drift.drift_total_before)


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
    takeaways = [
        _status_takeaway(result),
        _intent_count_takeaway(result),
        _cash_weight_takeaway(result),
    ]
    takeaways.extend(_optional_takeaways(request=request, result=result))
    return takeaways


def _status_takeaway(result: ProposalResult) -> ProposalArtifactTakeaway:
    return ProposalArtifactTakeaway(
        code="STATUS",
        value=f"Proposal status is {result.status}.",
    )


def _intent_count_takeaway(result: ProposalResult) -> ProposalArtifactTakeaway:
    security_trade_count = _intent_count(result, "SECURITY_TRADE")
    fx_intent_count = _intent_count(result, "FX_SPOT")
    return ProposalArtifactTakeaway(
        code="INTENTS",
        value=(
            f"Generated {security_trade_count} security trades and {fx_intent_count} FX intents."
        ),
    )


def _intent_count(result: ProposalResult, intent_type: str) -> int:
    return sum(1 for item in result.intents if item.intent_type == intent_type)


def _cash_weight_takeaway(result: ProposalResult) -> ProposalArtifactTakeaway:
    return ProposalArtifactTakeaway(
        code="CASH",
        value=(
            f"Cash weight changed from {quantized_weight_str(cash_weight(result.before))} "
            f"to {quantized_weight_str(cash_weight(result.after_simulated))}."
        ),
    )


def _optional_takeaways(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[ProposalArtifactTakeaway]:
    takeaways = []
    drift_takeaway = _drift_takeaway(result)
    if drift_takeaway is not None:
        takeaways.append(drift_takeaway)
    suitability_takeaway = _suitability_takeaway(request=request, result=result)
    if suitability_takeaway is not None:
        takeaways.append(suitability_takeaway)
    return takeaways


def _drift_takeaway(result: ProposalResult) -> ProposalArtifactTakeaway | None:
    if result.drift_analysis is None:
        return None
    drift_before = quantized_weight_str(result.drift_analysis.asset_class.drift_total_before)
    drift_after = quantized_weight_str(result.drift_analysis.asset_class.drift_total_after)
    return ProposalArtifactTakeaway(
        code="DRIFT",
        value=f"Asset-class drift changed from {drift_before} to {drift_after}.",
    )


def _suitability_takeaway(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactTakeaway | None:
    if not request.options.enable_suitability_scanner or result.suitability is None:
        return None
    summary = result.suitability.summary
    return ProposalArtifactTakeaway(
        code="SUITABILITY",
        value=(
            f"Suitability issues: new={summary.new_count}, "
            f"resolved={summary.resolved_count}, "
            f"persistent={summary.persistent_count}."
        ),
    )
