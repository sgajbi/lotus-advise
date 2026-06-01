from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.proposals.async_parameters import ProposalAsyncOperationIdPath
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.lifecycle_parameters import ProposalIdPath, ProposalVersionNoPath
from src.api.proposals.support_parameters import ProposalIdempotencyKeyPath
from src.api.proposals.support_responses import (
    SUPPORT_ASYNC_REPLAY_RESPONSES,
    SUPPORT_LINEAGE_RESPONSES,
    SUPPORT_VERSION_REPLAY_RESPONSES,
)
from src.core.proposals import (
    ProposalApprovalsResponse,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalWorkflowService,
    ProposalWorkflowTimelineResponse,
)
from src.core.replay.models import AdvisoryReplayEvidenceResponse


@shared.router.get(
    "/advisory/proposals/{proposal_id}/workflow-events",
    response_model=ProposalWorkflowTimelineResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Workflow Timeline",
    description=(
        "Returns append-only workflow event timeline for investigation, supportability, and audit."
    ),
)
def get_proposal_workflow_timeline(
    proposal_id: ProposalIdPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalWorkflowTimelineResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    return run_proposal_operation(lambda: service.get_workflow_timeline(proposal_id=proposal_id))


@shared.router.get(
    "/advisory/proposals/{proposal_id}/approvals",
    response_model=ProposalApprovalsResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Approvals",
    description=(
        "Returns approval/consent records for support investigations and workflow audit traces."
    ),
)
def get_proposal_approvals(
    proposal_id: ProposalIdPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalApprovalsResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    return run_proposal_operation(lambda: service.get_approvals(proposal_id=proposal_id))


@shared.router.get(
    "/advisory/proposals/{proposal_id}/lineage",
    response_model=ProposalLineageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Lineage",
    description=(
        "Returns immutable version lineage metadata with hashes "
        "for reproducibility and root-cause analysis."
    ),
    responses=SUPPORT_LINEAGE_RESPONSES,
)
def get_proposal_lineage(
    proposal_id: ProposalIdPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalLineageResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    return run_proposal_operation(lambda: service.get_lineage(proposal_id=proposal_id))


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/replay-evidence",
    response_model=AdvisoryReplayEvidenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Version Replay Evidence",
    description=(
        "Returns normalized replay evidence for an immutable proposal version, including "
        "context resolution, continuity links, and canonical hashes."
    ),
    responses=SUPPORT_VERSION_REPLAY_RESPONSES,
)
def get_proposal_version_replay_evidence(
    proposal_id: ProposalIdPath,
    version_no: ProposalVersionNoPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> AdvisoryReplayEvidenceResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    return run_proposal_operation(
        lambda: service.get_version_replay(proposal_id=proposal_id, version_no=version_no)
    )


@shared.router.get(
    "/advisory/proposals/idempotency/{idempotency_key}",
    response_model=ProposalIdempotencyLookupResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Lookup Proposal Idempotency Mapping",
    description=(
        "Returns idempotency-to-proposal mapping for support and retry investigation workflows."
    ),
)
def get_proposal_idempotency_lookup(
    idempotency_key: ProposalIdempotencyKeyPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalIdempotencyLookupResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    return run_proposal_operation(
        lambda: service.get_idempotency_lookup(idempotency_key=idempotency_key)
    )


@shared.router.get(
    "/advisory/proposals/operations/{operation_id}/replay-evidence",
    response_model=AdvisoryReplayEvidenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Operations & Support"],
    summary="Get Proposal Async Replay Evidence",
    description=(
        "Returns normalized replay evidence for an async proposal operation, linking async "
        "runtime truth to proposal version evidence when a terminal proposal result exists."
    ),
    responses=SUPPORT_ASYNC_REPLAY_RESPONSES,
)
def get_proposal_async_replay_evidence(
    operation_id: ProposalAsyncOperationIdPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> AdvisoryReplayEvidenceResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    return run_proposal_operation(
        lambda: service.get_async_operation_replay(operation_id=operation_id)
    )
