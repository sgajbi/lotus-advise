from src.core.advisor_cockpit.action_sources import (
    MemoPackageBlockedActionSource,
    PolicyReviewActionSource,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord

COCKPIT_POLICY_REVIEW_STATUSES = frozenset({"PENDING_REVIEW", "BLOCKED"})


def build_policy_review_sources(
    records: list[PolicyEvaluationRecord],
) -> list[PolicyReviewActionSource]:
    return [
        _policy_review_source(record)
        for record in records
        if record.evaluation_status in COCKPIT_POLICY_REVIEW_STATUSES
    ]


def build_memo_block_sources(
    *,
    records: list[ProposalMemoRecord],
    proposals: dict[str, ProposalRecord],
) -> list[MemoPackageBlockedActionSource]:
    return [
        source
        for record in records
        if (
            source := _memo_block_source(
                record,
                proposal=proposals.get(record.proposal_id),
            )
        )
        is not None
    ]


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


def _memo_block_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
) -> MemoPackageBlockedActionSource | None:
    blockage_code = _memo_blockage_code(record)
    if blockage_code is None:
        return None
    return MemoPackageBlockedActionSource(
        memo_id=record.memo_id,
        proposal_id=record.proposal_id,
        portfolio_id=proposal.portfolio_id if proposal is not None else None,
        blockage_code=blockage_code,
        summary="Proposal memo package is not ready for advisor-use packaging.",
        owner_role="REPORTING_OWNER",
        source_timestamp=record.created_at.isoformat(),
        materiality_rank=70 if record.memo_status == "BLOCKED" else 60,
        lineage_id=f"proposal_memo:{record.memo_id}",
        content_hash=record.memo_hash,
    )


def _memo_blockage_code(record: ProposalMemoRecord) -> str | None:
    if record.memo_status == "BLOCKED":
        return "MEMO_STATUS_BLOCKED"
    if record.lifecycle_status != "FINALIZED":
        return "MEMO_FINALIZATION_REQUIRED"
    if not record.review_events_json:
        return "MEMO_REVIEW_REQUIRED"
    return None


__all__ = [
    "COCKPIT_POLICY_REVIEW_STATUSES",
    "build_memo_block_sources",
    "build_policy_review_sources",
]
