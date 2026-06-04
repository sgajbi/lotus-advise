from __future__ import annotations

from typing import Any, cast

from src.core.proposals.exceptions import ProposalNotFoundError, ProposalValidationError
from src.core.proposals.memo_persistence_models import (
    ProposalMemoEventRecord,
    ProposalMemoRecord,
)
from src.core.proposals.memo_response_projection import latest_event_posture
from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.core.proposals.proposal_replay import load_proposal_version_replay_referents
from src.core.proposals.repository import ProposalRepository


def load_proposal_version_for_memo(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> tuple[ProposalRecord, ProposalVersionRecord]:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if referents.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if referents.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    return referents.proposal, referents.version


def load_memo_for_proposal_version(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalMemoRecord:
    memo = repository.get_memo_by_proposal_version(
        proposal_id=proposal_id,
        proposal_version_no=version_no,
    )
    if memo is None:
        raise ProposalNotFoundError("PROPOSAL_MEMO_NOT_FOUND")
    return memo


def require_advisor_use_review(
    *,
    memo: ProposalMemoRecord,
    events: list[ProposalMemoEventRecord],
) -> dict[str, Any]:
    posture = latest_event_posture(events, event_type="MEMO_REVIEW_RECORDED")
    if posture.get("review_action") != "APPROVE_FOR_ADVISOR_USE":
        raise ProposalValidationError("MEMO_REPORT_PACKAGE_REQUIRES_ADVISOR_USE_REVIEW")
    if posture.get("memo_hash") != memo.memo_hash:
        raise ProposalValidationError("MEMO_REVIEW_SOURCE_HASH_MISMATCH")
    return cast("dict[str, Any]", posture)


def validate_source_memo_hash(*, memo: ProposalMemoRecord, source_memo_hash: str) -> None:
    if source_memo_hash != memo.memo_hash:
        raise ProposalValidationError("MEMO_SOURCE_HASH_MISMATCH")
