from __future__ import annotations

from src.core.advisor_cockpit.source_read_model import (
    AdvisorCockpitSourceBatch,
    build_advisor_cockpit_source_read_model,
)
from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.source_projection_refs import projection_source_ref
from src.core.advisory_copilot.source_projection_text import projection_summary_item
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


def build_cockpit_actions_section(
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
