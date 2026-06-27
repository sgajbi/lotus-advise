from __future__ import annotations

from fastapi import Request, status

import src.api.proposals.router as shared
from src.api.observability import correlation_id_var
from src.api.proposals.errors import reject_unexpected_query_params
from src.api.proposals.idea_intake_parameters import IdeaProposalIntakeCorrelationIdHeader
from src.api.proposals.idea_intake_responses import IDEA_PROPOSAL_INTAKE_RESPONSES
from src.core.proposals.correlation import normalize_optional_correlation_id, resolve_correlation_id
from src.core.proposals.idea_proposal_intake import (
    IDEA_PROPOSAL_INTAKE_REQUEST_EXAMPLE,
    IdeaProposalIntakeRequest,
    IdeaProposalIntakeResponse,
    acknowledge_idea_proposal_intake,
)

_IDEA_PROPOSAL_INTAKE_DESCRIPTION = (
    "Accepts a source-safe lotus-idea conversion-intent handoff for advisory-side review. "
    "This route proves only an Advise-owned route foundation for future proposal lifecycle "
    "realization. It does not grant suitability, create an advisory proposal record, create "
    "orders, authorize client publication, or promote a supported feature."
)


@shared.router.post(
    "/advisory/proposals/idea-intake",
    response_model=IdeaProposalIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Advisory Proposal Lifecycle"],
    summary="Accept lotus-idea Proposal Intake Foundation",
    description=_IDEA_PROPOSAL_INTAKE_DESCRIPTION,
    responses=IDEA_PROPOSAL_INTAKE_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"example": IDEA_PROPOSAL_INTAKE_REQUEST_EXAMPLE}}
        }
    },
)
def accept_idea_proposal_intake(
    request: Request,
    payload: IdeaProposalIntakeRequest,
    correlation_id: IdeaProposalIntakeCorrelationIdHeader = None,
) -> IdeaProposalIntakeResponse:
    shared._assert_lifecycle_enabled()
    reject_unexpected_query_params(request, allowed_params=set())
    return acknowledge_idea_proposal_intake(
        payload,
        correlation_id=_resolved_intake_correlation_id(correlation_id),
    )


def _resolved_intake_correlation_id(correlation_id: str | None) -> str:
    return (
        normalize_optional_correlation_id(correlation_id)
        or correlation_id_var.get()
        or resolve_correlation_id(None)
    )
