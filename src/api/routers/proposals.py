import os
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status

from src.core.proposals import (
    ProposalApprovalsResponse,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDetailResponse,
    ProposalIdempotencyConflictError,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalTransitionError,
    ProposalValidationError,
    ProposalVersionDetail,
    ProposalVersionRequest,
    ProposalWorkflowService,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.models import ProposalApprovalRequest, ProposalListResponse
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository

router = APIRouter(tags=["Advisory Proposal Lifecycle"])

_REPOSITORY = InMemoryProposalRepository()
_SERVICE: Optional[ProposalWorkflowService] = None


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_proposal_workflow_service() -> ProposalWorkflowService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = ProposalWorkflowService(
            repository=_REPOSITORY,
            store_evidence_bundle=_env_flag("PROPOSAL_STORE_EVIDENCE_BUNDLE", True),
            require_expected_state=_env_flag("PROPOSAL_REQUIRE_EXPECTED_STATE", True),
            allow_portfolio_id_change_on_new_version=_env_flag(
                "PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION", False
            ),
            require_proposal_simulation_flag=_env_flag("PROPOSAL_REQUIRE_SIMULATION_FLAG", True),
        )
    return _SERVICE


def reset_proposal_workflow_service_for_tests() -> None:
    global _REPOSITORY
    global _SERVICE
    _REPOSITORY = InMemoryProposalRepository()
    _SERVICE = None


def _assert_lifecycle_enabled() -> None:
    if not _env_flag("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED",
        )


def _assert_support_apis_enabled() -> None:
    if not _env_flag("PROPOSAL_SUPPORT_APIS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PROPOSAL_SUPPORT_APIS_DISABLED",
        )


@router.post(
    "/rebalance/proposals",
    response_model=ProposalCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create and Persist Advisory Proposal",
    description=(
        "Runs advisory simulation + artifact generation and persists immutable proposal version, "
        "workflow creation event, and idempotency mapping."
    ),
)
def create_proposal(
    payload: ProposalCreateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for proposal-create deduplication.",
            examples=["proposal-create-idem-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id captured in lifecycle audit reason payload.",
            examples=["corr-proposal-create-001"],
        ),
    ] = None,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalCreateResponse:
    _assert_lifecycle_enabled()
    try:
        return service.create_proposal(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except ProposalIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get(
    "/rebalance/proposals/{proposal_id}",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal",
    description="Returns proposal summary, current immutable version, and last gate decision.",
)
def get_proposal(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    include_evidence: Annotated[
        bool,
        Query(
            description="Include full evidence bundle in current version payload.",
            examples=[True],
        ),
    ] = True,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalDetailResponse:
    _assert_lifecycle_enabled()
    try:
        return service.get_proposal(proposal_id=proposal_id, include_evidence=include_evidence)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/proposals",
    response_model=ProposalListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Proposals",
    description="Lists persisted proposals with optional filters and cursor pagination.",
)
def list_proposals(
    portfolio_id: Annotated[
        Optional[str], Query(description="Portfolio filter.", examples=["pf_01"])
    ] = None,
    state: Annotated[
        Optional[str],
        Query(description="Current workflow state filter.", examples=["DRAFT"]),
    ] = None,
    created_by: Annotated[
        Optional[str],
        Query(description="Creator actor id filter.", examples=["advisor_123"]),
    ] = None,
    created_from: Annotated[
        Optional[datetime],
        Query(
            description="Created-at lower bound in UTC ISO8601.", examples=["2026-02-19T00:00:00Z"]
        ),
    ] = None,
    created_to: Annotated[
        Optional[datetime],
        Query(
            description="Created-at upper bound in UTC ISO8601.", examples=["2026-02-20T00:00:00Z"]
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Page size.", ge=1, le=100, examples=[20]),
    ] = 20,
    cursor: Annotated[
        Optional[str],
        Query(description="Opaque cursor from previous list response.", examples=["pp_123"]),
    ] = None,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalListResponse:
    _assert_lifecycle_enabled()
    return service.list_proposals(
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/rebalance/proposals/{proposal_id}/versions/{version_no}",
    summary="Get Proposal Version",
    response_model=ProposalVersionDetail,
    status_code=status.HTTP_200_OK,
    description="Returns one immutable proposal version by version number.",
)
def get_proposal_version(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number.", ge=1, examples=[1]),
    ],
    include_evidence: Annotated[
        bool,
        Query(description="Include full evidence bundle in version payload.", examples=[True]),
    ] = True,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
):
    _assert_lifecycle_enabled()
    try:
        return service.get_version(
            proposal_id=proposal_id,
            version_no=version_no,
            include_evidence=include_evidence,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/rebalance/proposals/{proposal_id}/versions",
    response_model=ProposalCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Proposal Version",
    description=(
        "Creates a new immutable proposal version by rerunning simulation + artifact build."
    ),
)
def create_proposal_version(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalVersionRequest,
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id captured in version event reason payload.",
            examples=["corr-proposal-version-001"],
        ),
    ] = None,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalCreateResponse:
    _assert_lifecycle_enabled()
    try:
        return service.create_version(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProposalValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post(
    "/rebalance/proposals/{proposal_id}/transitions",
    response_model=ProposalStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition Proposal State",
    description=(
        "Applies one validated workflow transition with optimistic state concurrency check."
    ),
)
def transition_proposal_state(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalStateTransitionRequest,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalStateTransitionResponse:
    _assert_lifecycle_enabled()
    try:
        return service.transition_state(proposal_id=proposal_id, payload=payload)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProposalStateConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post(
    "/rebalance/proposals/{proposal_id}/approvals",
    response_model=ProposalStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Proposal Approval",
    description=(
        "Persists a structured approval/consent record and appends "
        "the corresponding workflow event "
        "with deterministic state transition."
    ),
)
def record_proposal_approval(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalApprovalRequest,
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalStateTransitionResponse:
    _assert_lifecycle_enabled()
    try:
        return service.record_approval(proposal_id=proposal_id, payload=payload)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProposalStateConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get(
    "/rebalance/proposals/{proposal_id}/workflow-events",
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
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalWorkflowTimelineResponse:
    _assert_lifecycle_enabled()
    _assert_support_apis_enabled()
    try:
        return service.get_workflow_timeline(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/proposals/{proposal_id}/approvals",
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
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalApprovalsResponse:
    _assert_lifecycle_enabled()
    _assert_support_apis_enabled()
    try:
        return service.get_approvals(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/proposals/{proposal_id}/lineage",
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
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalLineageResponse:
    _assert_lifecycle_enabled()
    _assert_support_apis_enabled()
    try:
        return service.get_lineage(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/proposals/idempotency/{idempotency_key}",
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
    service: Annotated[ProposalWorkflowService, Depends(get_proposal_workflow_service)] = None,
) -> ProposalIdempotencyLookupResponse:
    _assert_lifecycle_enabled()
    _assert_support_apis_enabled()
    try:
        return service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
