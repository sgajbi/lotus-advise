from __future__ import annotations

from types import MappingProxyType

from src.core.advisory_copilot.models import CopilotActionFamily, CopilotBusinessProjection

_BUSINESS_PROJECTIONS: dict[CopilotActionFamily, CopilotBusinessProjection] = {
    "PROPOSAL_EXPLANATION": CopilotBusinessProjection(
        action_family="PROPOSAL_EXPLANATION",
        label="Proposal explanation",
        summary="Explain source-backed proposal evidence for advisor review.",
        next_action_label="Review explanation",
    ),
    "EVIDENCE_QA": CopilotBusinessProjection(
        action_family="EVIDENCE_QA",
        label="Evidence question",
        summary="Answer bounded questions using cited advisory evidence only.",
        next_action_label="Review answer",
    ),
    "MEETING_PREPARATION": CopilotBusinessProjection(
        action_family="MEETING_PREPARATION",
        label="Meeting preparation",
        summary="Prepare an advisor-reviewed meeting note from current advisory evidence.",
        next_action_label="Review meeting note",
    ),
    "COMPLIANCE_REVIEW_SUMMARY": CopilotBusinessProjection(
        action_family="COMPLIANCE_REVIEW_SUMMARY",
        label="Compliance review summary",
        summary="Summarize policy, disclosure, blocker, and review evidence.",
        next_action_label="Review summary",
    ),
    "OPERATIONS_REPORT_HANDOFF": CopilotBusinessProjection(
        action_family="OPERATIONS_REPORT_HANDOFF",
        label="Operations and report handoff",
        summary="Summarize report readiness, blockers, and operational handoff posture.",
        next_action_label="Review handoff",
    ),
    "CLIENT_FOLLOW_UP_DRAFT": CopilotBusinessProjection(
        action_family="CLIENT_FOLLOW_UP_DRAFT",
        label="Client follow-up draft",
        summary="Draft advisor-reviewed client follow-up questions without sending them.",
        next_action_label="Review draft",
    ),
}

COPILOT_BUSINESS_PROJECTIONS = MappingProxyType(_BUSINESS_PROJECTIONS)


def business_projection_for_action(
    action_family: CopilotActionFamily,
) -> CopilotBusinessProjection:
    return COPILOT_BUSINESS_PROJECTIONS[action_family]

