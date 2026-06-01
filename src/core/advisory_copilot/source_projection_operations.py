from __future__ import annotations

from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.source_projection_refs import projection_source_ref
from src.core.advisory_copilot.source_projection_text import (
    latest_reference,
    projection_summary_item,
)
from src.core.proposals.models import (
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


def has_report_readiness(memo: ProposalMemoRecord) -> bool:
    return bool(memo.report_package_events_json or memo.archive_refs_json)


def build_report_readiness_section(*, memo: ProposalMemoRecord) -> CopilotEvidenceSectionInput:
    latest_report_ref = latest_reference(memo.report_package_events_json) or memo.memo_id
    latest_archive_ref = latest_reference(memo.archive_refs_json) or "Not recorded"
    return CopilotEvidenceSectionInput(
        section_key="REPORT_READINESS",
        title="Report readiness",
        evidence_class="OPERATIONS_HANDOFF_EVIDENCE",
        source_refs=(
            projection_source_ref(
                source_type="MEMO_REPORT_PACKAGE",
                source_id=latest_report_ref,
                content_hash=memo.memo_hash,
                access_class="OPERATIONS_HANDOFF_EVIDENCE",
            ),
        ),
        summary_items=(
            "Advisor-use report package evidence is recorded for the memo.",
            projection_summary_item(f"Latest archive reference posture: {latest_archive_ref}."),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "OPERATIONS_SUPPORT"),
    )


def has_operations_handoff(events: list[ProposalWorkflowEventRecord]) -> bool:
    return any(
        str(event.event_type).startswith("EXECUTION") or event.event_type == "EXECUTED"
        for event in events
    )


def build_operations_handoff_section(
    *, proposal: ProposalRecord, events: list[ProposalWorkflowEventRecord]
) -> CopilotEvidenceSectionInput:
    execution_events = [
        event
        for event in events
        if str(event.event_type).startswith("EXECUTION") or event.event_type == "EXECUTED"
    ]
    latest = sorted(execution_events, key=lambda item: (item.occurred_at, item.event_id))[-1]
    return CopilotEvidenceSectionInput(
        section_key="OPERATIONS_HANDOFF",
        title="Operations handoff",
        evidence_class="OPERATIONS_HANDOFF_EVIDENCE",
        source_refs=(
            projection_source_ref(
                source_type="PROPOSAL_WORKFLOW_EVENT",
                source_id=latest.event_id,
                content_hash=None,
                access_class="OPERATIONS_HANDOFF_EVIDENCE",
            ),
        ),
        summary_items=(
            projection_summary_item(
                f"Latest implementation handoff posture is {latest.event_type}."
            ),
            projection_summary_item(
                f"Proposal {proposal.proposal_id} remains source-owned for lifecycle state."
            ),
        ),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "OPERATIONS_SUPPORT"),
    )
