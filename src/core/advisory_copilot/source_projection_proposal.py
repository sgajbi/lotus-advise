from __future__ import annotations

from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.source_projection_refs import projection_source_ref
from src.core.advisory_copilot.source_projection_text import (
    projection_summary_item,
    safe_nested_string,
)
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord, ProposalVersionRecord


def build_proposal_context_section(
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


def build_narrative_posture_section(
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


def build_memo_evidence_section(*, memo: ProposalMemoRecord) -> CopilotEvidenceSectionInput:
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
