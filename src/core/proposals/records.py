from datetime import datetime

from src.core.proposals.models import (
    ProposalIdempotencyRecord,
    ProposalLifecycleOrigin,
    ProposalRecord,
)


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
