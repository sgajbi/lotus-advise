from src.core.advisory.decision_material_changes import build_material_changes
from src.core.advisory.decision_requirements import build_approval_requirements
from src.core.advisory.decision_summary_models import (
    ProposalDecisionActionItem,
    ProposalDecisionClientMandatePosture,
    ProposalDecisionMissingEvidence,
    ProposalDecisionNextAction,
    ProposalDecisionRiskPosture,
    ProposalDecisionStatus,
    ProposalDecisionSuitabilityPosture,
    ProposalDecisionSummary,
)
from src.core.advisory.decision_summary_status_rules import (
    decision_confidence,
    derive_decision_status,
    primary_decision_reason_code,
    primary_decision_summary,
    recommended_decision_next_action,
)
from src.core.advisory.explanation_contracts import (
    ADVISORY_POLICY_CONTEXT_EXPLANATION_KEY,
    AUTHORITY_RESOLUTION_EXPLANATION_KEY,
    authority_resolution_from_explanation,
    policy_context_from_explanation,
)
from src.core.advisory.policy_context import client_context_available, mandate_context_available
from src.core.proposal_result_models import ProposalResult
from src.core.suitability_models import SuitabilityIssue, SuitabilityResult

_DECISION_POLICY_VERSION = "advisory-decision-policy.2026-04"
_EXPLANATION_EVIDENCE_REF_PATHS = (
    (AUTHORITY_RESOLUTION_EXPLANATION_KEY, "proposal.explanation.authority_resolution"),
    (ADVISORY_POLICY_CONTEXT_EXPLANATION_KEY, "proposal.explanation.advisory_policy_context"),
)


def build_proposal_decision_summary(result: ProposalResult) -> ProposalDecisionSummary:
    missing_evidence = _build_missing_evidence(result)
    decision_status = derive_decision_status(result, missing_evidence)
    approval_requirements = build_approval_requirements(
        result=result,
        missing_evidence=missing_evidence,
        policy_version=_DECISION_POLICY_VERSION,
    )
    material_changes = build_material_changes(
        result=result,
        approval_requirements=approval_requirements,
        missing_evidence=missing_evidence,
    )
    primary_reason_code = primary_decision_reason_code(result, missing_evidence, decision_status)
    primary_summary = primary_decision_summary(decision_status, primary_reason_code)
    recommended_next_action = recommended_decision_next_action(decision_status, missing_evidence)
    confidence = decision_confidence(result, missing_evidence)
    evidence_refs = _build_evidence_refs(result, missing_evidence)
    advisor_action_items = _build_action_items(
        decision_status=decision_status,
        recommended_next_action=recommended_next_action,
        primary_reason_code=primary_reason_code,
        primary_summary=primary_summary,
        evidence_refs=evidence_refs,
    )

    return ProposalDecisionSummary(
        decision_status=decision_status,
        top_level_status=result.status,
        primary_reason_code=primary_reason_code,
        primary_summary=primary_summary,
        recommended_next_action=recommended_next_action,
        decision_policy_version=_DECISION_POLICY_VERSION,
        suitability_policy_version=(
            result.suitability.policy_version if result.suitability is not None else None
        ),
        confidence=confidence,
        approval_requirements=approval_requirements,
        material_changes=material_changes,
        suitability_posture=_build_suitability_posture(result.suitability),
        missing_evidence=missing_evidence,
        risk_posture=_build_risk_posture(result),
        client_and_mandate_posture=_build_client_and_mandate_posture(result),
        advisor_action_items=advisor_action_items,
        evidence_refs=evidence_refs,
    )


def _build_suitability_posture(
    suitability: SuitabilityResult | None,
) -> ProposalDecisionSuitabilityPosture | None:
    if suitability is None:
        return ProposalDecisionSuitabilityPosture(
            status="NOT_AVAILABLE",
            issue_count_new=0,
            issue_count_resolved=0,
            issue_count_persistent=0,
            highest_severity_new=None,
            recommended_gate=None,
        )
    return ProposalDecisionSuitabilityPosture(
        status="AVAILABLE",
        issue_count_new=suitability.summary.new_count,
        issue_count_resolved=suitability.summary.resolved_count,
        issue_count_persistent=suitability.summary.persistent_count,
        highest_severity_new=suitability.summary.highest_severity_new,
        recommended_gate=suitability.recommended_gate,
    )


def _build_risk_posture(result: ProposalResult) -> ProposalDecisionRiskPosture:
    risk_lens = result.explanation.get("risk_lens")
    authority_resolution = authority_resolution_from_explanation(result.explanation)
    if isinstance(risk_lens, dict):
        return ProposalDecisionRiskPosture(
            status="AVAILABLE",
            source_service=_string_or_none(risk_lens.get("source_service")),
            summary="Risk lens evidence is available from canonical upstream enrichment.",
        )
    if authority_resolution is not None and authority_resolution.risk_authority == "unavailable":
        return ProposalDecisionRiskPosture(
            status="UNAVAILABLE",
            source_service=None,
            summary="Risk lens evidence is unavailable for this proposal run.",
        )
    return ProposalDecisionRiskPosture(
        status="UNAVAILABLE",
        source_service=None,
        summary="Risk lens evidence was not attached to this proposal result.",
    )


def _build_client_and_mandate_posture(
    result: ProposalResult,
) -> ProposalDecisionClientMandatePosture:
    policy_context = policy_context_from_explanation(result.explanation)
    if policy_context is None:
        return ProposalDecisionClientMandatePosture(
            status="NOT_EVALUATED",
            summary="Client and mandate posture was not attached to this proposal result.",
        )

    policy_context_payload = policy_context.model_dump(exclude_none=True)
    client_available = client_context_available(policy_context_payload)
    mandate_available = mandate_context_available(policy_context_payload)
    if client_available and mandate_available:
        return ProposalDecisionClientMandatePosture(
            status="AVAILABLE",
            summary="Client and mandate context are available for policy evaluation.",
        )
    return ProposalDecisionClientMandatePosture(
        status="PARTIAL",
        summary="Client or mandate context is incomplete for policy evaluation.",
    )


def _build_missing_evidence(result: ProposalResult) -> list[ProposalDecisionMissingEvidence]:
    items = _market_data_missing_evidence(result)
    risk_evidence = _risk_missing_evidence(result)
    if risk_evidence is not None:
        items.append(risk_evidence)
    items.extend(_suitability_missing_evidence(result))
    return items


def _market_data_missing_evidence(result: ProposalResult) -> list[ProposalDecisionMissingEvidence]:
    data_quality = result.diagnostics.data_quality
    items: list[ProposalDecisionMissingEvidence] = []
    if data_quality.get("price_missing"):
        items.append(_price_missing_evidence(blocking=result.status == "BLOCKED"))
    if data_quality.get("fx_missing"):
        items.append(_fx_missing_evidence(blocking=result.status == "BLOCKED"))
    return items


def _price_missing_evidence(*, blocking: bool) -> ProposalDecisionMissingEvidence:
    return ProposalDecisionMissingEvidence(
        evidence_type="MARKET_PRICE",
        reason_code="MISSING_REQUIRED_MARKET_PRICE",
        summary="Required price data is missing for one or more instruments.",
        blocking=blocking,
        evidence_refs=["proposal.diagnostics.data_quality.price_missing"],
    )


def _fx_missing_evidence(*, blocking: bool) -> ProposalDecisionMissingEvidence:
    return ProposalDecisionMissingEvidence(
        evidence_type="FX_RATE",
        reason_code="MISSING_REQUIRED_FX_DATA",
        summary="Required FX data is missing for one or more currency pairs.",
        blocking=blocking,
        evidence_refs=["proposal.diagnostics.data_quality.fx_missing"],
    )


def _risk_missing_evidence(result: ProposalResult) -> ProposalDecisionMissingEvidence | None:
    authority_resolution = authority_resolution_from_explanation(result.explanation)
    if authority_resolution is None or authority_resolution.risk_authority != "unavailable":
        return None
    return ProposalDecisionMissingEvidence(
        evidence_type="RISK_LENS",
        reason_code="MISSING_RISK_LENS",
        summary="Canonical risk evidence is unavailable for this proposal run.",
        blocking=True,
        evidence_refs=["proposal.explanation.authority_resolution"],
    )


def _suitability_missing_evidence(
    result: ProposalResult,
) -> list[ProposalDecisionMissingEvidence]:
    if result.suitability is None:
        return []
    items: list[ProposalDecisionMissingEvidence] = []
    for issue in result.suitability.issues:
        missing_evidence = _missing_evidence_from_suitability_issue(result, issue)
        if missing_evidence is not None:
            items.append(missing_evidence)
    return items


def _missing_evidence_from_suitability_issue(
    result: ProposalResult,
    issue: SuitabilityIssue,
) -> ProposalDecisionMissingEvidence | None:
    if issue.dimension == "DATA_QUALITY":
        return ProposalDecisionMissingEvidence(
            evidence_type="SUITABILITY_DATA_QUALITY",
            reason_code=issue.issue_id,
            summary=issue.summary,
            blocking=result.status == "BLOCKED" and issue.severity == "HIGH",
            evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
        )
    if issue.classification != "UNKNOWN_DUE_TO_MISSING_EVIDENCE":
        return None
    return ProposalDecisionMissingEvidence(
        evidence_type="SUITABILITY_CONTEXT",
        reason_code=issue.issue_id,
        summary=issue.summary,
        blocking=issue.severity == "HIGH" or result.status != "READY",
        evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
    )


def _build_evidence_refs(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> list[str]:
    refs = [
        *_proposal_state_evidence_refs(result),
        *_explanation_evidence_refs(result),
        *_missing_evidence_refs(missing_evidence),
    ]
    return sorted(set(refs))


def _proposal_state_evidence_refs(result: ProposalResult) -> list[str]:
    refs = ["proposal.status"]
    if result.gate_decision is not None:
        refs.append("proposal.gate_decision")
    if result.suitability is not None:
        refs.append("proposal.suitability")
    return refs


def _explanation_evidence_refs(result: ProposalResult) -> list[str]:
    return [
        evidence_ref
        for explanation_key, evidence_ref in _EXPLANATION_EVIDENCE_REF_PATHS
        if result.explanation.get(explanation_key) is not None
    ]


def _missing_evidence_refs(
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> list[str]:
    return [evidence_ref for item in missing_evidence for evidence_ref in item.evidence_refs]


def _build_action_items(
    *,
    decision_status: ProposalDecisionStatus,
    recommended_next_action: ProposalDecisionNextAction,
    primary_reason_code: str,
    primary_summary: str,
    evidence_refs: list[str],
) -> list[ProposalDecisionActionItem]:
    return [
        ProposalDecisionActionItem(
            action_code=recommended_next_action,
            reason_code=primary_reason_code,
            summary=primary_summary,
            evidence_refs=evidence_refs,
        )
    ]


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
