from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.lifecycle_parameters import (
    ProposalCreateCorrelationIdHeader,
    ProposalCreatedByFilterQuery,
    ProposalCreatedFromFilterQuery,
    ProposalCreatedToFilterQuery,
    ProposalCreateIdempotencyKeyHeader,
    ProposalIdPath,
    ProposalIncludeEvidenceQuery,
    ProposalListCursorQuery,
    ProposalListLimitQuery,
    ProposalNarrativeVersionNoPath,
    ProposalOptionalApprovalIdempotencyKeyHeader,
    ProposalOptionalNarrativeReviewIdempotencyKeyHeader,
    ProposalOptionalTransitionIdempotencyKeyHeader,
    ProposalPortfolioIdFilterQuery,
    ProposalVersionCorrelationIdHeader,
    ProposalVersionIncludeEvidenceQuery,
    ProposalVersionNoPath,
    ProposalWorkflowStateFilterQuery,
)
from src.api.proposals.lifecycle_responses import (
    PROPOSAL_CREATE_RESPONSES,
    PROPOSAL_NARRATIVE_READ_RESPONSES,
    PROPOSAL_NARRATIVE_REGENERATE_RESPONSES,
    PROPOSAL_NARRATIVE_REVIEW_RESPONSES,
    PROPOSAL_VERSION_CREATE_RESPONSES,
)
from src.core.advisory.narrative_models import ProposalNarrativeReviewRequest
from src.core.proposals import (
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDetailResponse,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalVersionDetail,
    ProposalVersionRequest,
    ProposalWorkflowService,
)
from src.core.proposals.models import (
    ProposalApprovalRequest,
    ProposalListResponse,
    ProposalNarrativeReadResponse,
    ProposalNarrativeRegenerationRequest,
    ProposalNarrativeRegenerationResponse,
    ProposalNarrativeReviewResponse,
)


@shared.router.post(
    "/advisory/proposals",
    response_model=ProposalCreateResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Create and Persist Advisory Proposal",
    description=(
        "Runs advisory simulation + artifact generation and persists immutable proposal version, "
        "workflow creation event, and idempotency mapping. Supports legacy direct "
        "`simulate_request` payloads plus normalized `stateless` and `stateful` input modes."
    ),
    responses=PROPOSAL_CREATE_RESPONSES,
)
def create_proposal(
    payload: ProposalCreateRequest,
    idempotency_key: ProposalCreateIdempotencyKeyHeader,
    correlation_id: ProposalCreateCorrelationIdHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalCreateResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.create_proposal(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Get Proposal",
    description="Returns proposal summary, current immutable version, and last gate decision.",
)
def get_proposal(
    proposal_id: ProposalIdPath,
    include_evidence: ProposalIncludeEvidenceQuery = True,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalDetailResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.get_proposal(proposal_id=proposal_id, include_evidence=include_evidence)
    )


@shared.router.get(
    "/advisory/proposals",
    response_model=ProposalListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="List Proposals",
    description="Lists persisted proposals with optional filters and cursor pagination.",
)
def list_proposals(
    portfolio_id: ProposalPortfolioIdFilterQuery = None,
    state: ProposalWorkflowStateFilterQuery = None,
    created_by: ProposalCreatedByFilterQuery = None,
    created_from: ProposalCreatedFromFilterQuery = None,
    created_to: ProposalCreatedToFilterQuery = None,
    limit: ProposalListLimitQuery = 20,
    cursor: ProposalListCursorQuery = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalListResponse:
    shared._assert_lifecycle_enabled()
    return service.list_proposals(
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}",
    summary="Get Proposal Version",
    response_model=ProposalVersionDetail,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    description="Returns one immutable proposal version by version number.",
)
def get_proposal_version(
    proposal_id: ProposalIdPath,
    version_no: ProposalVersionNoPath,
    include_evidence: ProposalVersionIncludeEvidenceQuery = True,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalVersionDetail:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.get_version(
            proposal_id=proposal_id,
            version_no=version_no,
            include_evidence=include_evidence,
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions",
    response_model=ProposalCreateResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Create Proposal Version",
    description=(
        "Creates a new immutable proposal version by rerunning simulation + artifact build. "
        "Supports legacy direct `simulate_request` payloads plus normalized `stateless` and "
        "`stateful` input modes."
    ),
    responses=PROPOSAL_VERSION_CREATE_RESPONSES,
)
def create_proposal_version(
    proposal_id: ProposalIdPath,
    payload: ProposalVersionRequest,
    correlation_id: ProposalVersionCorrelationIdHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalCreateResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.create_version(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/transitions",
    response_model=ProposalStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Transition Proposal State",
    description=(
        "Applies one validated workflow transition with optimistic state concurrency check."
    ),
)
def transition_proposal_state(
    proposal_id: ProposalIdPath,
    payload: ProposalStateTransitionRequest,
    idempotency_key: ProposalOptionalTransitionIdempotencyKeyHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalStateTransitionResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.transition_state(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/approvals",
    response_model=ProposalStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Record Proposal Approval",
    description=(
        "Persists a structured approval/consent record and appends "
        "the corresponding workflow event "
        "with deterministic state transition."
    ),
)
def record_proposal_approval(
    proposal_id: ProposalIdPath,
    payload: ProposalApprovalRequest,
    idempotency_key: ProposalOptionalApprovalIdempotencyKeyHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalStateTransitionResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.record_approval(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/regenerate",
    response_model=ProposalNarrativeRegenerationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Regenerate Proposal Narrative Candidate",
    description=(
        "Builds a non-persisted advisor-review narrative candidate from the immutable proposal "
        "version artifact. This route does not mutate proposal state, does not replace the "
        "persisted narrative, and does not publish client-ready commentary."
    ),
    responses=PROPOSAL_NARRATIVE_REGENERATE_RESPONSES,
)
def regenerate_proposal_narrative(
    proposal_id: ProposalIdPath,
    version_no: ProposalNarrativeVersionNoPath,
    payload: ProposalNarrativeRegenerationRequest,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalNarrativeRegenerationResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.regenerate_narrative(
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
        )
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative",
    response_model=ProposalNarrativeReadResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Read Persisted Proposal Narrative",
    description=(
        "Returns the exact proposal narrative persisted on an immutable proposal version, plus "
        "latest review posture and source hash evidence. The route is read-only and never "
        "regenerates text."
    ),
    responses=PROPOSAL_NARRATIVE_READ_RESPONSES,
)
def get_proposal_narrative(
    proposal_id: ProposalIdPath,
    version_no: ProposalNarrativeVersionNoPath,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalNarrativeReadResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.get_narrative(proposal_id=proposal_id, version_no=version_no)
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review",
    response_model=ProposalNarrativeReviewResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Lifecycle"],
    summary="Review Persisted Proposal Narrative",
    description=(
        "Records an idempotent review decision against the immutable narrative stored on a "
        "proposal version. The operation never regenerates narrative text and preserves exact "
        "review, policy, guardrail, and source-hash evidence for replay."
    ),
    responses=PROPOSAL_NARRATIVE_REVIEW_RESPONSES,
)
def review_proposal_narrative(
    proposal_id: ProposalIdPath,
    version_no: ProposalNarrativeVersionNoPath,
    payload: ProposalNarrativeReviewRequest,
    idempotency_key: ProposalOptionalNarrativeReviewIdempotencyKeyHeader = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalNarrativeReviewResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: service.record_narrative_review(
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    )
