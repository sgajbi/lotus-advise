import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from src.core.dpm_runs import (
    DpmAsyncOperationStatusResponse,
    DpmRunArtifactResponse,
    DpmRunIdempotencyLookupResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmRunWorkflowActionRequest,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.models import RebalanceResult
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository

router = APIRouter(tags=["DPM Run Supportability"])

_REPOSITORY = InMemoryDpmRunRepository()
_SERVICE: Optional[DpmRunSupportService] = None


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 1 else default


def _env_csv_set(name: str, default: set[str]) -> set[str]:
    value = os.getenv(name)
    if value is None:
        return set(default)
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or set(default)


def _assert_support_apis_enabled() -> None:
    if not _env_flag("DPM_SUPPORT_APIS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_SUPPORT_APIS_DISABLED",
        )


def _assert_async_operations_enabled() -> None:
    if not _env_flag("DPM_ASYNC_OPERATIONS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_OPERATIONS_DISABLED",
        )


def _assert_artifacts_enabled() -> None:
    if not _env_flag("DPM_ARTIFACTS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ARTIFACTS_DISABLED",
        )


def _assert_workflow_enabled() -> None:
    if not _env_flag("DPM_WORKFLOW_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_WORKFLOW_DISABLED",
        )


def get_dpm_run_support_service() -> DpmRunSupportService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = DpmRunSupportService(
            repository=_REPOSITORY,
            async_operation_ttl_seconds=_env_int(
                "DPM_ASYNC_OPERATIONS_TTL_SECONDS",
                86400,
            ),
            workflow_enabled=_env_flag("DPM_WORKFLOW_ENABLED", False),
            workflow_requires_review_for_statuses=_env_csv_set(
                "DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES",
                {"PENDING_REVIEW"},
            ),
        )
    return _SERVICE


def record_dpm_run_for_support(
    *,
    result: RebalanceResult,
    request_hash: str,
    portfolio_id: str,
    idempotency_key: Optional[str],
) -> None:
    service = get_dpm_run_support_service()
    service.record_run(
        result=result,
        request_hash=request_hash,
        portfolio_id=portfolio_id,
        idempotency_key=idempotency_key,
    )


def reset_dpm_run_support_service_for_tests() -> None:
    global _REPOSITORY
    global _SERVICE
    _REPOSITORY = InMemoryDpmRunRepository()
    _SERVICE = None


@router.get(
    "/rebalance/runs/by-correlation/{correlation_id}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run by Correlation Id",
    description="Returns the latest DPM run mapped to a correlation id for investigation.",
)
def get_run_by_correlation(
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_run_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/idempotency/{idempotency_key}",
    response_model=DpmRunIdempotencyLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Idempotency Mapping",
    description="Returns DPM idempotency key to run mapping for support investigations.",
)
def get_run_idempotency_lookup(
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunIdempotencyLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run by Run Id",
    description="Returns one DPM run payload and lineage metadata by run id.",
)
def get_run_by_run_id(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_run(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}/artifact",
    response_model=DpmRunArtifactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Artifact by Run Id",
    description=(
        "Returns deterministic run artifact synthesized from persisted DPM run payload "
        "and supportability metadata."
    ),
)
def get_run_artifact_by_run_id(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunArtifactResponse:
    _assert_support_apis_enabled()
    _assert_artifacts_enabled()
    try:
        return service.get_run_artifact(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/operations/{operation_id}",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Async Operation",
    description="Returns asynchronous operation status and terminal result/error payload.",
)
def get_dpm_async_operation(
    operation_id: Annotated[
        str,
        Path(description="Asynchronous operation identifier.", examples=["dop_001"]),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmAsyncOperationStatusResponse:
    _assert_support_apis_enabled()
    _assert_async_operations_enabled()
    try:
        return service.get_async_operation(operation_id=operation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/operations/by-correlation/{correlation_id}",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Async Operation by Correlation Id",
    description="Returns asynchronous operation associated with correlation id.",
)
def get_dpm_async_operation_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier associated with async operation."),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmAsyncOperationStatusResponse:
    _assert_support_apis_enabled()
    _assert_async_operations_enabled()
    try:
        return service.get_async_operation_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow State",
    description=(
        "Returns workflow gate state and latest decision for run-level review supportability."
    ),
)
def get_dpm_run_workflow(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunWorkflowResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.get_workflow(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow State by Correlation Id",
    description="Returns workflow gate state for run resolved by correlation id.",
)
def get_dpm_run_workflow_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier used on run submission."),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunWorkflowResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.get_workflow_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow State by Idempotency Key",
    description="Returns workflow gate state for run resolved by idempotency key mapping.",
)
def get_dpm_run_workflow_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(description="Idempotency key supplied to `/rebalance/simulate`."),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunWorkflowResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.get_workflow_by_idempotency(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/rebalance/runs/{rebalance_run_id}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply DPM Run Workflow Action",
    description=(
        "Applies one workflow action (`APPROVE`, `REJECT`, `REQUEST_CHANGES`) and returns "
        "updated workflow state."
    ),
)
def apply_dpm_run_workflow_action(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-001"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.apply_workflow_action(
            rebalance_run_id=rebalance_run_id,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            correlation_id=correlation_id or "c_none",
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow History",
    description=(
        "Returns append-only workflow decision history for run-level audit and investigation."
    ),
)
def get_dpm_run_workflow_history(
    rebalance_run_id: Annotated[
        str,
        Path(description="DPM run identifier.", examples=["rr_abc12345"]),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunWorkflowHistoryResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.get_workflow_history(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow History by Correlation Id",
    description="Returns workflow decision history for run resolved by correlation id.",
)
def get_dpm_run_workflow_history_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier used on run submission."),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunWorkflowHistoryResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.get_workflow_history_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow/history",
    response_model=DpmRunWorkflowHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Run Workflow History by Idempotency Key",
    description="Returns workflow decision history for run resolved by idempotency key mapping.",
)
def get_dpm_run_workflow_history_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(description="Idempotency key supplied to `/rebalance/simulate`."),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunWorkflowHistoryResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.get_workflow_history_by_idempotency(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
