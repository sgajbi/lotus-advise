from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.core.advisory.narrative_models import ProposalNarrativeReviewRequest
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.models import (
    ProposalNarrativeReadResponse,
    ProposalNarrativeRegenerationRequest,
    ProposalNarrativeRegenerationResponse,
    ProposalNarrativeReviewResponse,
)
from src.core.proposals.narrative_read_model import (
    build_narrative_read_response,
    build_narrative_regeneration_response,
)
from src.core.proposals.narrative_review import (
    ProposalNarrativeReviewError,
    record_narrative_review_event,
)
from src.core.proposals.proposal_replay import load_proposal_version_replay_referents
from src.core.proposals.repository import ProposalRepository


def build_narrative_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalNarrativeReadResponse:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if referents.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if referents.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    try:
        return build_narrative_read_response(
            proposal=referents.proposal,
            version=referents.version,
            events=referents.events,
        )
    except ProposalNarrativeReviewError as exc:
        raise ProposalValidationError(str(exc)) from exc


def regenerate_narrative_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalNarrativeRegenerationRequest,
) -> ProposalNarrativeRegenerationResponse:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if referents.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if referents.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    try:
        return build_narrative_regeneration_response(
            proposal=referents.proposal,
            version=referents.version,
            events=referents.events,
            payload=payload,
        )
    except ProposalNarrativeReviewError as exc:
        raise ProposalValidationError(str(exc)) from exc


def record_narrative_review(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalNarrativeReviewRequest,
    idempotency_key: str | None,
    event_id: str,
    occurred_at: Callable[[], datetime],
) -> ProposalNarrativeReviewResponse:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if referents.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if referents.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    try:
        return record_narrative_review_event(
            repository=repository,
            event_id=event_id,
            proposal=referents.proposal,
            version=referents.version,
            payload=payload,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at(),
        )
    except ProposalNarrativeReviewError as exc:
        message = str(exc)
        if message.startswith("IDEMPOTENCY_KEY_CONFLICT"):
            raise ProposalIdempotencyConflictError(message) from exc
        raise ProposalValidationError(message) from exc


__all__ = [
    "build_narrative_view",
    "record_narrative_review",
    "regenerate_narrative_view",
]
