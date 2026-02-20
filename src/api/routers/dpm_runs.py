import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status

from src.core.dpm_runs import (
    DpmAsyncOperationStatusResponse,
    DpmRunArtifactResponse,
    DpmRunIdempotencyLookupResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
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


def get_dpm_run_support_service() -> DpmRunSupportService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = DpmRunSupportService(repository=_REPOSITORY)
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
