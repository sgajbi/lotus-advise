from __future__ import annotations

from types import MappingProxyType

from src.core.advisory_copilot.models import CopilotActionDefinition
from src.core.advisory_copilot.type_models import CopilotActionFamily

_ACTION_DEFINITIONS: dict[CopilotActionFamily, CopilotActionDefinition] = {
    "PROPOSAL_EXPLANATION": CopilotActionDefinition(
        action_family="PROPOSAL_EXPLANATION",
        display_name="Proposal explanation",
        business_purpose="Explain source-backed proposal evidence for advisor review.",
        supported_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
        required_source_dependencies=(
            "RFC0023_PROPOSAL_NARRATIVE",
            "RFC0024_PROPOSAL_MEMO",
            "RFC0025_POLICY_EVALUATION",
        ),
        output_evidence_classes=("ADVISOR_USE_SUMMARY", "COMPLIANCE_REVIEW_EVIDENCE"),
        workflow_pack_id="advisory_copilot_proposal_explanation.pack",
        workbench_surface_key="advisory_copilot.proposal_explanation",
    ),
    "EVIDENCE_QA": CopilotActionDefinition(
        action_family="EVIDENCE_QA",
        display_name="Evidence question",
        business_purpose="Answer bounded questions using cited advisory evidence only.",
        supported_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
        required_source_dependencies=(
            "RFC0023_PROPOSAL_NARRATIVE",
            "RFC0024_PROPOSAL_MEMO",
            "RFC0025_POLICY_EVALUATION",
            "RFC0026_ADVISOR_COCKPIT",
        ),
        output_evidence_classes=("ADVISOR_USE_SUMMARY", "MODEL_RISK_AUDIT"),
        workflow_pack_id="advisory_copilot_evidence_qa.pack",
        workbench_surface_key="advisory_copilot.evidence_qa",
    ),
    "MEETING_PREPARATION": CopilotActionDefinition(
        action_family="MEETING_PREPARATION",
        display_name="Meeting preparation",
        business_purpose="Prepare an advisor-reviewed meeting note from current advisory evidence.",
        supported_audiences=("ADVISOR", "DESK_HEAD"),
        required_source_dependencies=(
            "RFC0024_PROPOSAL_MEMO",
            "RFC0025_POLICY_EVALUATION",
            "RFC0026_ADVISOR_COCKPIT",
        ),
        output_evidence_classes=("ADVISOR_USE_SUMMARY",),
        workflow_pack_id="advisory_copilot_meeting_preparation.pack",
        workbench_surface_key="advisory_copilot.meeting_preparation",
    ),
    "COMPLIANCE_REVIEW_SUMMARY": CopilotActionDefinition(
        action_family="COMPLIANCE_REVIEW_SUMMARY",
        display_name="Compliance review summary",
        business_purpose="Summarize policy, disclosure, blocker, and review evidence.",
        supported_audiences=("COMPLIANCE_REVIEWER", "DESK_HEAD", "MODEL_RISK_OPERATOR"),
        required_source_dependencies=(
            "RFC0023_PROPOSAL_NARRATIVE",
            "RFC0024_PROPOSAL_MEMO",
            "RFC0025_POLICY_EVALUATION",
        ),
        output_evidence_classes=("COMPLIANCE_REVIEW_EVIDENCE", "MODEL_RISK_AUDIT"),
        workflow_pack_id="advisory_copilot_compliance_review_summary.pack",
        workbench_surface_key="advisory_copilot.compliance_review_summary",
    ),
    "OPERATIONS_REPORT_HANDOFF": CopilotActionDefinition(
        action_family="OPERATIONS_REPORT_HANDOFF",
        display_name="Operations and report handoff",
        business_purpose="Summarize report readiness, blockers, and operational handoff posture.",
        supported_audiences=("ADVISOR", "OPERATIONS_SUPPORT", "DESK_HEAD"),
        required_source_dependencies=(
            "RFC0024_PROPOSAL_MEMO",
            "RFC0026_ADVISOR_COCKPIT",
            "REPORT_READINESS",
            "OPERATIONS_HANDOFF",
        ),
        output_evidence_classes=("OPERATIONS_HANDOFF_EVIDENCE", "INTERNAL_SUPPORTABILITY"),
        workflow_pack_id="advisory_copilot_operations_report_handoff.pack",
        workbench_surface_key="advisory_copilot.operations_report_handoff",
    ),
    "CLIENT_FOLLOW_UP_DRAFT": CopilotActionDefinition(
        action_family="CLIENT_FOLLOW_UP_DRAFT",
        display_name="Client follow-up draft",
        business_purpose="Draft advisor-reviewed client follow-up questions without sending them.",
        supported_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
        required_source_dependencies=(
            "RFC0024_PROPOSAL_MEMO",
            "RFC0025_POLICY_EVALUATION",
            "RFC0026_ADVISOR_COCKPIT",
        ),
        output_evidence_classes=("ADVISOR_USE_SUMMARY", "COMPLIANCE_REVIEW_EVIDENCE"),
        workflow_pack_id="advisory_copilot_client_follow_up_draft.pack",
        workbench_surface_key="advisory_copilot.client_follow_up_draft",
    ),
}

COPILOT_ACTION_CATALOG = MappingProxyType(_ACTION_DEFINITIONS)


def list_copilot_action_definitions() -> tuple[CopilotActionDefinition, ...]:
    return tuple(COPILOT_ACTION_CATALOG.values())


def get_copilot_action_definition(
    action_family: CopilotActionFamily,
) -> CopilotActionDefinition:
    return COPILOT_ACTION_CATALOG[action_family]
