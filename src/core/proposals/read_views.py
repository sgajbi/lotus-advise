from __future__ import annotations

from datetime import datetime

from src.core.proposals.approval_read_model import load_proposal_approval_read_model
from src.core.proposals.detail_read_model import load_proposal_detail_read_model
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.idempotency_read_model import load_proposal_idempotency_read_model
from src.core.proposals.lineage_read_model import load_proposal_lineage_read_model
from src.core.proposals.list_read_model import load_proposal_list_read_model
from src.core.proposals.models import (
    ProposalApprovalsResponse,
    ProposalDetailResponse,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalListResponse,
    ProposalVersionDetail,
)
from src.core.proposals.projections import (
    build_approvals_response,
    build_proposal_lineage_response,
    build_proposal_list_response,
    to_idempotency_lookup_response,
    to_proposal_summary,
    to_version_detail,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.version_read_model import load_proposal_version_read_model


def build_proposal_detail_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    include_evidence: bool,
) -> ProposalDetailResponse:
    detail = load_proposal_detail_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if detail.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if detail.current_version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    current_version = to_version_detail(
        detail.current_version,
        include_evidence=include_evidence,
    )
    return ProposalDetailResponse(
        proposal=to_proposal_summary(detail.proposal),
        current_version=current_version,
        last_gate_decision=current_version.gate_decision,
    )


def build_proposal_list_view(
    *,
    repository: ProposalRepository,
    portfolio_id: str | None,
    state: str | None,
    created_by: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    limit: int,
    cursor: str | None,
) -> ProposalListResponse:
    read_model = load_proposal_list_read_model(
        repository=repository,
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )
    return build_proposal_list_response(
        proposals=read_model.proposals,
        next_cursor=read_model.next_cursor,
    )


def build_proposal_approvals_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalApprovalsResponse:
    approval_read_model = load_proposal_approval_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if approval_read_model.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    return build_approvals_response(
        proposal=approval_read_model.proposal,
        approvals=approval_read_model.approvals,
    )


def build_proposal_lineage_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalLineageResponse:
    lineage = load_proposal_lineage_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if lineage.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

    return build_proposal_lineage_response(
        proposal=lineage.proposal,
        versions_by_number=lineage.versions_by_number,
    )


def build_idempotency_lookup_view(
    *,
    repository: ProposalRepository,
    idempotency_key: str,
) -> ProposalIdempotencyLookupResponse:
    read_model = load_proposal_idempotency_read_model(
        repository=repository,
        idempotency_key=idempotency_key,
    )
    if read_model.record is None:
        raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND")
    return to_idempotency_lookup_response(read_model.record)


def build_proposal_version_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    include_evidence: bool,
) -> ProposalVersionDetail:
    read_model = load_proposal_version_read_model(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if read_model.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    return to_version_detail(read_model.version, include_evidence=include_evidence)


__all__ = [
    "build_idempotency_lookup_view",
    "build_proposal_approvals_view",
    "build_proposal_detail_view",
    "build_proposal_lineage_view",
    "build_proposal_list_view",
    "build_proposal_version_view",
]
