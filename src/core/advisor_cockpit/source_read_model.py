from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.advisor_cockpit.action_factory import (
    MeetingPreparationActionSource,
    MemoPackageBlockedActionSource,
    PolicyReviewActionSource,
    SupportabilityDegradedActionSource,
    UnsupportedCapabilityActionSource,
    build_first_wave_cockpit_actions,
)
from src.core.advisor_cockpit.models import AdvisoryActionItem
from src.core.policy_packs.models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord

ACTIVE_PROPOSAL_STATES = frozenset(
    {
        "DRAFT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "AWAITING_CLIENT_CONSENT",
        "EXECUTION_READY",
    }
)
COCKPIT_POLICY_REVIEW_STATUSES = frozenset({"PENDING_REVIEW", "BLOCKED"})


class AdvisorCockpitSourceBatch(BaseModel):
    proposals: list[ProposalRecord] = Field(
        default_factory=list,
        description="Preloaded proposal records in the bounded cockpit scope.",
    )
    policy_evaluations: list[PolicyEvaluationRecord] = Field(
        default_factory=list,
        description="Preloaded policy evaluation records in the bounded cockpit scope.",
    )
    memos: list[ProposalMemoRecord] = Field(
        default_factory=list,
        description="Preloaded proposal memo records in the bounded cockpit scope.",
    )
    supportability_events: list[SupportabilityDegradedActionSource] = Field(
        default_factory=list,
        description="Preloaded source dependency readiness events.",
    )
    unsupported_capabilities: list[UnsupportedCapabilityActionSource] = Field(
        default_factory=list,
        description="Explicit unsupported capability markers for the bounded scope.",
    )


class AdvisorCockpitSourceReadModel(BaseModel):
    source_counts: dict[str, int] = Field(
        description="Counts of preloaded source records consumed by the read model."
    )
    policy_reviews: list[PolicyReviewActionSource] = Field(
        description="Policy evaluation sources requiring cockpit action."
    )
    memo_blocks: list[MemoPackageBlockedActionSource] = Field(
        description="Memo sources requiring blocked package attention."
    )
    meeting_preparations: list[MeetingPreparationActionSource] = Field(
        description="Meeting-preparation sources for active advisory proposals."
    )
    supportability_events: list[SupportabilityDegradedActionSource] = Field(
        description="Source dependency readiness events."
    )
    unsupported_capabilities: list[UnsupportedCapabilityActionSource] = Field(
        description="Unsupported capability markers that must remain visible."
    )
    action_items: list[AdvisoryActionItem] = Field(
        description="Sorted first-wave cockpit action items derived from the source batch."
    )


def build_advisor_cockpit_source_read_model(
    batch: AdvisorCockpitSourceBatch,
) -> AdvisorCockpitSourceReadModel:
    policy_reviews = [
        _policy_review_source(record)
        for record in batch.policy_evaluations
        if record.evaluation_status in COCKPIT_POLICY_REVIEW_STATUSES
    ]
    memo_blocks = [
        source for record in batch.memos if (source := _memo_block_source(record)) is not None
    ]
    meeting_preparations = [
        _meeting_preparation_source(record)
        for record in batch.proposals
        if record.current_state in ACTIVE_PROPOSAL_STATES
    ]
    action_items = build_first_wave_cockpit_actions(
        policy_reviews=policy_reviews,
        memo_blocks=memo_blocks,
        meeting_preparations=meeting_preparations,
        supportability_events=batch.supportability_events,
        unsupported_capabilities=batch.unsupported_capabilities,
    )
    return AdvisorCockpitSourceReadModel(
        source_counts={
            "proposals": len(batch.proposals),
            "policy_evaluations": len(batch.policy_evaluations),
            "memos": len(batch.memos),
            "supportability_events": len(batch.supportability_events),
            "unsupported_capabilities": len(batch.unsupported_capabilities),
        },
        policy_reviews=policy_reviews,
        memo_blocks=memo_blocks,
        meeting_preparations=meeting_preparations,
        supportability_events=list(batch.supportability_events),
        unsupported_capabilities=list(batch.unsupported_capabilities),
        action_items=action_items,
    )


def _policy_review_source(record: PolicyEvaluationRecord) -> PolicyReviewActionSource:
    return PolicyReviewActionSource(
        policy_evaluation_id=record.evaluation_id,
        portfolio_id=record.portfolio_id,
        proposal_id=record.proposal_id,
        policy_result=record.evaluation_status,
        summary="Policy evaluation requires review before client-ready posture can change.",
        source_timestamp=record.generated_at,
        materiality_rank=90 if record.evaluation_status == "BLOCKED" else 80,
        lineage_id=f"policy_evaluation:{record.evaluation_id}",
        content_hash=record.evaluation_hash,
    )


def _memo_block_source(record: ProposalMemoRecord) -> MemoPackageBlockedActionSource | None:
    blockage_code = _memo_blockage_code(record)
    if blockage_code is None:
        return None
    return MemoPackageBlockedActionSource(
        memo_id=record.memo_id,
        proposal_id=record.proposal_id,
        blockage_code=blockage_code,
        summary="Proposal memo package is not ready for advisor-use packaging.",
        owner_role="REPORTING_OWNER",
        source_timestamp=record.created_at.isoformat(),
        materiality_rank=70 if record.memo_status == "BLOCKED" else 60,
        lineage_id=f"proposal_memo:{record.memo_id}",
        content_hash=record.memo_hash,
    )


def _meeting_preparation_source(record: ProposalRecord) -> MeetingPreparationActionSource:
    return MeetingPreparationActionSource(
        preparation_id=f"prep_{record.proposal_id}_v{record.current_version_no}",
        context_ref=record.proposal_id,
        context_type="PROPOSAL",
        portfolio_id=record.portfolio_id,
        proposal_id=record.proposal_id,
        summary="Active advisory proposal is available for meeting preparation.",
        source_timestamp=record.last_event_at.isoformat(),
        materiality_rank=50 if record.current_state == "EXECUTION_READY" else 30,
    )


def _memo_blockage_code(record: ProposalMemoRecord) -> str | None:
    if record.memo_status == "BLOCKED":
        return "MEMO_STATUS_BLOCKED"
    if record.lifecycle_status != "FINALIZED":
        return "MEMO_FINALIZATION_REQUIRED"
    if not record.review_events_json:
        return "MEMO_REVIEW_REQUIRED"
    return None
