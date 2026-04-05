from typing import Annotated

from fastapi import Depends, Path, status

import src.api.proposals.router as shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.core.proposals import (
    ProposalApprovalsResponse,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalNotFoundError,
    ProposalWorkflowService,
    ProposalWorkflowTimelineResponse,
)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/workflow-events",
    response_model=ProposalWorkflowTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Workflow Timeline",
    description=(
        "Returns append-only workflow event timeline for investigation, supportability, and audit."
    ),
)
def get_proposal_workflow_timeline(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalWorkflowTimelineResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_workflow_timeline(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/approvals",
    response_model=ProposalApprovalsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Approvals",
    description=(
        "Returns approval/consent records for support investigations and workflow audit traces."
    ),
)
def get_proposal_approvals(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalApprovalsResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_approvals(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/lineage",
    response_model=ProposalLineageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Lineage",
    description=(
        "Returns immutable version lineage metadata with hashes "
        "for reproducibility and root-cause analysis."
    ),
)
def get_proposal_lineage(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalLineageResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_lineage(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/idempotency/{idempotency_key}",
    response_model=ProposalIdempotencyLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup Proposal Idempotency Mapping",
    description=(
        "Returns idempotency-to-proposal mapping for support and retry investigation workflows."
    ),
)
def get_proposal_idempotency_lookup(
    idempotency_key: Annotated[
        str,
        Path(
            description="Proposal create idempotency key.",
            examples=["proposal-create-idem-001"],
        ),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalIdempotencyLookupResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)
