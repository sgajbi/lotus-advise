from fastapi import BackgroundTasks, Depends, status

import src.api.proposals.router as shared
from src.api.proposals.async_parameters import (
    ProposalAsyncCorrelationIdHeader,
    ProposalAsyncCorrelationIdPath,
    ProposalAsyncCreateIdempotencyKeyHeader,
    ProposalAsyncOperationIdPath,
)
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.lifecycle_parameters import ProposalIdPath
from src.core.proposals import (
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalVersionRequest,
    ProposalWorkflowService,
)


@shared.router.post(
    "/advisory/proposals/async",
    response_model=ProposalAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Advisory Proposal Lifecycle"],
    summary="Create and Persist Advisory Proposal Asynchronously",
    description=(
        "Accepts proposal creation request for asynchronous processing. "
        "Use returned operation id or correlation id to retrieve status and result."
    ),
)
def create_proposal_async(
    payload: ProposalCreateRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: ProposalAsyncCreateIdempotencyKeyHeader,
    correlation_id: ProposalAsyncCorrelationIdHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncAcceptedResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    accepted, should_schedule = run_proposal_operation(
        lambda: service.accept_create_proposal_async_submission(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    )
    if should_schedule:
        background_tasks.add_task(
            service.execute_create_proposal_async,
            operation_id=accepted.operation_id,
        )
    return accepted


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/async",
    response_model=ProposalAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Advisory Proposal Lifecycle"],
    summary="Create Proposal Version Asynchronously",
    description=(
        "Accepts proposal-version creation request for asynchronous processing. "
        "Use returned operation id or correlation id to retrieve status and result."
    ),
)
def create_proposal_version_async(
    proposal_id: ProposalIdPath,
    payload: ProposalVersionRequest,
    background_tasks: BackgroundTasks,
    correlation_id: ProposalAsyncCorrelationIdHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncAcceptedResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    accepted, should_schedule = run_proposal_operation(
        lambda: service.accept_create_version_async_submission(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )
    )
    if should_schedule:
        background_tasks.add_task(
            service.execute_create_version_async,
            operation_id=accepted.operation_id,
        )
    return accepted


@shared.router.get(
    "/advisory/proposals/operations/{operation_id}",
    response_model=ProposalAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Async Operation",
    description="Returns asynchronous operation status and terminal result/error payload.",
)
def get_proposal_async_operation(
    operation_id: ProposalAsyncOperationIdPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncOperationStatusResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    return run_proposal_operation(lambda: service.get_async_operation(operation_id=operation_id))


@shared.router.get(
    "/advisory/proposals/operations/by-correlation/{correlation_id}",
    response_model=ProposalAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Async Operation by Correlation Id",
    description="Returns the latest asynchronous operation associated with correlation id.",
)
def get_proposal_async_operation_by_correlation(
    correlation_id: ProposalAsyncCorrelationIdPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncOperationStatusResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    return run_proposal_operation(
        lambda: service.get_async_operation_by_correlation(correlation_id=correlation_id)
    )
