import os
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status

from src.core.dpm_runs import (
    DpmAsyncOperationListResponse,
    DpmAsyncOperationStatusResponse,
    DpmLineageResponse,
    DpmRunArtifactResponse,
    DpmRunIdempotencyHistoryResponse,
    DpmRunIdempotencyLookupResponse,
    DpmRunListResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmRunWorkflowActionRequest,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmSupportabilitySummaryResponse,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.models import RebalanceResult
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository, SqliteDpmRunRepository

router = APIRouter(tags=["DPM Run Supportability"])

_REPOSITORY = None
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


def _env_non_negative_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


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


def _assert_lineage_apis_enabled() -> None:
    if not _env_flag("DPM_LINEAGE_APIS_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_LINEAGE_APIS_DISABLED",
        )


def _assert_idempotency_history_apis_enabled() -> None:
    if not _env_flag("DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED",
        )


def _assert_supportability_summary_apis_enabled() -> None:
    if not _env_flag("DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED",
        )


def _supportability_store_backend_name() -> str:
    backend = os.getenv("DPM_SUPPORTABILITY_STORE_BACKEND", "IN_MEMORY").strip().upper()
    return "SQLITE" if backend == "SQLITE" else "IN_MEMORY"


def _build_repository():
    if _supportability_store_backend_name() == "SQLITE":
        sqlite_path = os.getenv("DPM_SUPPORTABILITY_SQLITE_PATH", ".data/dpm_supportability.db")
        return SqliteDpmRunRepository(database_path=sqlite_path)
    return InMemoryDpmRunRepository()


def get_dpm_run_support_service() -> DpmRunSupportService:
    global _REPOSITORY
    global _SERVICE
    if _REPOSITORY is None:
        _REPOSITORY = _build_repository()
    if _SERVICE is None:
        _SERVICE = DpmRunSupportService(
            repository=_REPOSITORY,
            async_operation_ttl_seconds=_env_int(
                "DPM_ASYNC_OPERATIONS_TTL_SECONDS",
                86400,
            ),
            supportability_retention_days=_env_non_negative_int(
                "DPM_SUPPORTABILITY_RETENTION_DAYS",
                0,
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
    _REPOSITORY = _build_repository()
    _SERVICE = None


@router.get(
    "/rebalance/runs",
    response_model=DpmRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List DPM Runs",
    description=(
        "Returns paginated DPM runs filtered by creation time range, run status, and portfolio id."
    ),
)
def list_runs(
    created_from: Annotated[
        Optional[datetime],
        Query(
            alias="from",
            description="Run creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[datetime],
        Query(
            alias="to",
            description="Run creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str],
        Query(
            alias="status",
            description="Optional run status filter.",
            examples=["READY"],
        ),
    ] = None,
    portfolio_id: Annotated[
        Optional[str],
        Query(
            description="Optional portfolio identifier filter.",
            examples=["pf_123"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of rows returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque cursor value returned by previous page.",
            examples=["rr_abc12345"],
        ),
    ] = None,
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunListResponse:
    _assert_support_apis_enabled()
    return service.list_runs(
        created_from=created_from,
        created_to=created_to,
        status=status_filter,
        portfolio_id=portfolio_id,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/rebalance/supportability/summary",
    response_model=DpmSupportabilitySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Supportability Summary",
    description=(
        "Returns supportability storage summary metrics (runs, operations, status counts, "
        "and temporal bounds) for operational investigation without direct database access."
    ),
)
def get_dpm_supportability_summary(
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmSupportabilitySummaryResponse:
    _assert_support_apis_enabled()
    _assert_supportability_summary_apis_enabled()
    return service.get_supportability_summary(
        store_backend=_supportability_store_backend_name(),
        retention_days=_env_non_negative_int("DPM_SUPPORTABILITY_RETENTION_DAYS", 0),
    )


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
    "/rebalance/idempotency/{idempotency_key}/history",
    response_model=DpmRunIdempotencyHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Idempotency History",
    description=(
        "Returns append-only run mapping history for one idempotency key, including request hash "
        "and correlation context for support investigations."
    ),
)
def get_run_idempotency_history(
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmRunIdempotencyHistoryResponse:
    _assert_support_apis_enabled()
    _assert_idempotency_history_apis_enabled()
    try:
        return service.get_idempotency_history(idempotency_key=idempotency_key)
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
    "/rebalance/operations",
    response_model=DpmAsyncOperationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List DPM Async Operations",
    description=(
        "Returns paginated async operations filtered by creation time range, "
        "status, operation type, and correlation id."
    ),
)
def list_dpm_async_operations(
    created_from: Annotated[
        Optional[datetime],
        Query(
            alias="from",
            description="Operation creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[datetime],
        Query(
            alias="to",
            description="Operation creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    operation_type: Annotated[
        Optional[str],
        Query(
            description="Optional operation type filter.",
            examples=["ANALYZE_SCENARIOS"],
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str],
        Query(
            alias="status",
            description="Optional operation status filter.",
            examples=["SUCCEEDED"],
        ),
    ] = None,
    correlation_id: Annotated[
        Optional[str],
        Query(
            description="Optional correlation id filter.",
            examples=["corr-dpm-async-001"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of rows returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque cursor value returned by previous page.",
            examples=["dop_001"],
        ),
    ] = None,
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmAsyncOperationListResponse:
    _assert_support_apis_enabled()
    _assert_async_operations_enabled()
    return service.list_async_operations(
        created_from=created_from,
        created_to=created_to,
        operation_type=operation_type,
        status=status_filter,
        correlation_id=correlation_id,
        limit=limit,
        cursor=cursor,
    )


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
    "/rebalance/lineage/{entity_id}",
    response_model=DpmLineageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPM Supportability Lineage by Entity Id",
    description=(
        "Returns supportability lineage edges for an entity id, including correlation, "
        "idempotency, run, and operation relations."
    ),
)
def get_dpm_lineage(
    entity_id: Annotated[
        str,
        Path(
            description=(
                "Supportability entity identifier such as correlation id, idempotency key, "
                "run id, or operation id."
            ),
            examples=["corr-1234-abcd"],
        ),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
) -> DpmLineageResponse:
    _assert_support_apis_enabled()
    _assert_lineage_apis_enabled()
    return service.get_lineage(entity_id=entity_id)


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


@router.post(
    "/rebalance/runs/by-correlation/{correlation_id}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply DPM Run Workflow Action by Correlation Id",
    description=(
        "Applies one workflow action for run resolved by correlation id and returns updated "
        "workflow state."
    ),
)
def apply_dpm_run_workflow_action_by_correlation(
    correlation_id: Annotated[
        str,
        Path(description="Correlation identifier used on run submission."),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
    action_correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-action-001"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.apply_workflow_action_by_correlation(
            correlation_id=correlation_id,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            action_correlation_id=action_correlation_id or "c_none",
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DpmWorkflowTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/rebalance/runs/idempotency/{idempotency_key}/workflow/actions",
    response_model=DpmRunWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply DPM Run Workflow Action by Idempotency Key",
    description=(
        "Applies one workflow action for run resolved by idempotency key mapping and returns "
        "updated workflow state."
    ),
)
def apply_dpm_run_workflow_action_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(description="Idempotency key supplied to `/rebalance/simulate`."),
    ],
    payload: DpmRunWorkflowActionRequest,
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)] = None,
    action_correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id for workflow action request tracing.",
            examples=["corr-workflow-action-002"],
        ),
    ] = None,
) -> DpmRunWorkflowResponse:
    _assert_support_apis_enabled()
    _assert_workflow_enabled()
    try:
        return service.apply_workflow_action_by_idempotency(
            idempotency_key=idempotency_key,
            action=payload.action,
            reason_code=payload.reason_code,
            comment=payload.comment,
            actor_id=payload.actor_id,
            action_correlation_id=action_correlation_id or "c_none",
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
