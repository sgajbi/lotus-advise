from __future__ import annotations

from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.source_projection_cockpit import build_cockpit_actions_section
from src.core.advisory_copilot.source_projection_operations import (
    build_operations_handoff_section,
    build_report_readiness_section,
    has_operations_handoff,
    has_report_readiness,
)
from src.core.advisory_copilot.source_projection_policy import build_policy_posture_section
from src.core.advisory_copilot.source_projection_proposal import (
    build_memo_evidence_section,
    build_narrative_posture_section,
    build_proposal_context_section,
)
from src.core.advisory_copilot.source_projection_text import (
    bounded_projection_reference,
    projection_identifier,
)
from src.core.advisory_copilot.type_models import CopilotActionFamily
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)

EVIDENCE_PACKET_ID_MAX_LENGTH = 160
LINEAGE_REF_ID_MAX_LENGTH = 160


def build_proposal_version_source_sections(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    memo: ProposalMemoRecord | None,
    memos: list[ProposalMemoRecord],
    approvals: list[ProposalApprovalRecordData],
    events: list[ProposalWorkflowEventRecord],
    policy_evaluations: list[PolicyEvaluationRecord],
) -> tuple[CopilotEvidenceSectionInput, ...]:
    sections = [
        build_proposal_context_section(proposal=proposal, version=version),
        build_narrative_posture_section(proposal=proposal, version=version),
        build_cockpit_actions_section(
            proposal=proposal,
            memos=memos,
            approvals=approvals,
            events=events,
            policy_evaluations=policy_evaluations,
        ),
    ]
    if memo is not None:
        sections.append(build_memo_evidence_section(memo=memo))
        if has_report_readiness(memo):
            sections.append(build_report_readiness_section(memo=memo))
    if policy_evaluations:
        sections.append(build_policy_posture_section(policy_evaluations=policy_evaluations))
    if has_operations_handoff(events):
        sections.append(build_operations_handoff_section(proposal=proposal, events=events))
    return tuple(sections)


def default_proposal_version_packet_id(
    *, action_family: CopilotActionFamily, proposal_id: str, version_no: int
) -> str:
    return bounded_projection_reference(
        projection_identifier(
            f"copilot_packet_{action_family.lower()}_{proposal_id}_v{version_no}"
        ),
        max_length=EVIDENCE_PACKET_ID_MAX_LENGTH,
    )
