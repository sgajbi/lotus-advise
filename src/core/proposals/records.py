from dataclasses import dataclass
from datetime import datetime

from src.core.proposals.lifecycle_events import build_proposal_created_event
from src.core.proposals.models import (
    ProposalIdempotencyRecord,
    ProposalLifecycleOrigin,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


@dataclass(frozen=True)
class ProposalCreateCommandState:
    proposal: ProposalRecord
    created_event: ProposalWorkflowEventRecord
    idempotency_record: ProposalIdempotencyRecord


def build_proposal_record(
    *,
    proposal_id: str,
    portfolio_id: str,
    mandate_id: str | None,
    jurisdiction: str | None,
    created_by: str,
    created_at: datetime,
    version_no: int,
    title: str | None,
    advisor_notes: str | None,
    lifecycle_origin: ProposalLifecycleOrigin,
    source_workspace_id: str | None,
) -> ProposalRecord:
    return ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        jurisdiction=jurisdiction,
        created_by=created_by,
        created_at=created_at,
        last_event_at=created_at,
        current_state="DRAFT",
        current_version_no=version_no,
        title=title,
        advisor_notes=advisor_notes,
        lifecycle_origin=lifecycle_origin,
        source_workspace_id=source_workspace_id,
    )


def build_proposal_idempotency_record(
    *,
    idempotency_key: str,
    request_hash: str,
    proposal_id: str,
    proposal_version_no: int,
    created_at: datetime,
) -> ProposalIdempotencyRecord:
    return ProposalIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        proposal_id=proposal_id,
        proposal_version_no=proposal_version_no,
        created_at=created_at,
    )


def build_proposal_create_command_state(
    *,
    proposal_id: str,
    portfolio_id: str,
    mandate_id: str | None,
    jurisdiction: str | None,
    created_by: str,
    created_at: datetime,
    version_no: int,
    title: str | None,
    advisor_notes: str | None,
    lifecycle_origin: ProposalLifecycleOrigin,
    source_workspace_id: str | None,
    event_id: str,
    correlation_id: str | None,
    idempotency_key: str,
    request_hash: str,
) -> ProposalCreateCommandState:
    proposal = build_proposal_record(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        jurisdiction=jurisdiction,
        created_by=created_by,
        created_at=created_at,
        version_no=version_no,
        title=title,
        advisor_notes=advisor_notes,
        lifecycle_origin=lifecycle_origin,
        source_workspace_id=source_workspace_id,
    )
    created_event = build_proposal_created_event(
        event_id=event_id,
        proposal_id=proposal_id,
        actor_id=created_by,
        occurred_at=created_at,
        related_version_no=version_no,
        correlation_id=correlation_id,
    )
    idempotency_record = build_proposal_idempotency_record(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        proposal_id=proposal_id,
        proposal_version_no=version_no,
        created_at=created_at,
    )
    return ProposalCreateCommandState(
        proposal=proposal,
        created_event=created_event,
        idempotency_record=idempotency_record,
    )
