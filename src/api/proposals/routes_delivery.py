from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

import src.api.proposals.router as shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.api.services.proposal_reporting_service import request_proposal_report
from src.core.proposals import (
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
    ProposalExecutionStatusResponse,
    ProposalNotFoundError,
    ProposalReportRequest,
    ProposalReportResponse,
    ProposalStateConflictError,
    ProposalValidationError,
    ProposalWorkflowService,
)
from src.integrations.lotus_report import LotusReportUnavailableError


@shared.router.post(
    "/advisory/proposals/{proposal_id}/report-requests",
    response_model=ProposalReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Advisory Proposal Report",
    description=(
        "Requests a Lotus-branded advisory report payload through the lotus-report seam without "
        "moving reporting ownership into lotus-advise."
    ),
)
def create_proposal_report_request(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalReportRequest,
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalReportResponse:
    shared._assert_lifecycle_enabled()
    try:
        return request_proposal_report(proposal_id=proposal_id, payload=payload, service=service)
    except (ProposalNotFoundError, ProposalValidationError) as exc:
        raise_proposal_http_exception(exc)
    except LotusReportUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@shared.router.post(
    "/advisory/proposals/{proposal_id}/execution-handoffs",
    response_model=ProposalExecutionHandoffResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Advisory Execution Handoff",
    description=(
        "Records an auditable execution handoff request while keeping execution ownership outside "
        "lotus-advise."
    ),
)
def request_execution_handoff(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalExecutionHandoffRequest,
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalExecutionHandoffResponse:
    shared._assert_lifecycle_enabled()
    try:
        return service.request_execution_handoff(proposal_id=proposal_id, payload=payload)
    except (ProposalNotFoundError, ProposalStateConflictError, ProposalValidationError) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/execution-status",
    response_model=ProposalExecutionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Advisory Execution Status",
    description=(
        "Returns advisory-owned execution handoff correlation state derived from append-only "
        "workflow history."
    ),
)
def get_execution_status(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalExecutionStatusResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_execution_status(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)
