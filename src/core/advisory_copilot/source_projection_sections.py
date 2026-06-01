from __future__ import annotations

from src.core.advisor_cockpit.source_read_model import (
    AdvisorCockpitSourceBatch,
    build_advisor_cockpit_source_read_model,
)
from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.source_projection_operations import (
    build_operations_handoff_section,
    build_report_readiness_section,
    has_operations_handoff,
    has_report_readiness,
)
from src.core.advisory_copilot.source_projection_policy import build_policy_posture_section
from src.core.advisory_copilot.source_projection_refs import projection_source_ref
from src.core.advisory_copilot.source_projection_text import (
    bounded_projection_reference,
    projection_identifier,
    projection_summary_item,
    safe_nested_string,
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
        _proposal_context_section(proposal=proposal, version=version),
        _narrative_posture_section(proposal=proposal, version=version),
        _cockpit_actions_section(
            proposal=proposal,
            memos=memos,
            approvals=approvals,
            events=events,
            policy_evaluations=policy_evaluations,
        ),
    ]
    if memo is not None:
        sections.append(_memo_evidence_section(memo=memo))
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


def _proposal_context_section(
    *, proposal: ProposalRecord, version: ProposalVersionRecord
) -> CopilotEvidenceSectionInput:
    return CopilotEvidenceSectionInput(
        section_key="PROPOSAL_CONTEXT",
        title="Proposal context",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=(
            projection_source_ref(
                source_type="PROPOSAL_VERSION",
                source_id=version.proposal_version_id,
                content_hash=version.artifact_hash,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=(
            projection_summary_item(
                f"{proposal.title or 'Advisory proposal'} is in {proposal.current_state} "
                f"for portfolio {proposal.portfolio_id}."
            ),
            projection_summary_item(
                f"Proposal version {version.version_no} was created with "
                f"{version.status_at_creation} source readiness."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER", "OPERATIONS_SUPPORT"),
    )


def _narrative_posture_section(
    *, proposal: ProposalRecord, version: ProposalVersionRecord
) -> CopilotEvidenceSectionInput:
    narrative_status = safe_nested_string(
        version.artifact_json,
        "narrative",
        "status",
    ) or safe_nested_string(version.artifact_json, "narrative_status")
    if not narrative_status:
        narrative_status = str(version.status_at_creation)
    return CopilotEvidenceSectionInput(
        section_key="NARRATIVE_POSTURE",
        title="Proposal narrative posture",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=(
            projection_source_ref(
                source_type="PROPOSAL_NARRATIVE",
                source_id=version.proposal_version_id,
                content_hash=version.artifact_hash,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=(
            projection_summary_item(
                f"Advisor-use proposal narrative posture is {narrative_status}."
            ),
            projection_summary_item(
                f"Client-ready publication remains blocked for proposal {proposal.proposal_id}."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
    )


def _memo_evidence_section(*, memo: ProposalMemoRecord) -> CopilotEvidenceSectionInput:
    return CopilotEvidenceSectionInput(
        section_key="MEMO_EVIDENCE",
        title="Proposal memo evidence",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=(
            projection_source_ref(
                source_type="PROPOSAL_MEMO",
                source_id=memo.memo_id,
                content_hash=memo.memo_hash,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=(
            projection_summary_item(f"Proposal memo {memo.memo_id} is {memo.memo_status}."),
            projection_summary_item(f"Memo lifecycle posture is {memo.lifecycle_status}."),
            (
                "Memo evidence remains advisor-use only until source review and publication "
                "gates pass."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER", "OPERATIONS_SUPPORT"),
    )


def _cockpit_actions_section(
    *,
    proposal: ProposalRecord,
    memos: list[ProposalMemoRecord],
    approvals: list[ProposalApprovalRecordData],
    events: list[ProposalWorkflowEventRecord],
    policy_evaluations: list[PolicyEvaluationRecord],
) -> CopilotEvidenceSectionInput:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[proposal],
            policy_evaluations=policy_evaluations,
            memos=memos,
            approvals=approvals,
            workflow_events=events,
        )
    )
    action_items = read_model.action_items[:5]
    summaries = [
        projection_summary_item(f"{item.title} is {item.status}; owner is {item.owner_role}.")
        for item in action_items
    ] or ["No advisor cockpit action is currently open for this proposal."]
    return CopilotEvidenceSectionInput(
        section_key="COCKPIT_ACTIONS",
        title="Advisor cockpit actions",
        evidence_class="ADVISOR_USE_SUMMARY",
        source_refs=tuple(
            projection_source_ref(
                source_type="ADVISOR_COCKPIT_ACTION",
                source_id=item.action_item_id,
                content_hash=None,
                access_class="ADVISOR_USE_SUMMARY",
            )
            for item in action_items
        )
        or (
            projection_source_ref(
                source_type="ADVISOR_COCKPIT_SCOPE",
                source_id=proposal.proposal_id,
                content_hash=None,
                access_class="ADVISOR_USE_SUMMARY",
            ),
        ),
        summary_items=tuple(summaries),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER", "OPERATIONS_SUPPORT"),
    )
