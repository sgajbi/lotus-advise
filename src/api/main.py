"""
FILE: src/api/main.py
"""

import logging
import os
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from src.api.persistence_profile import validate_persistence_profile_guardrails
from src.api.routers.dpm_policy_packs import (
    load_dpm_policy_pack_catalog,
    resolve_dpm_policy_pack,
)
from src.api.routers.dpm_policy_packs import router as dpm_policy_pack_router
from src.api.routers.dpm_runs import (
    get_dpm_run_support_service,
    record_dpm_run_for_support,
)
from src.api.routers.dpm_runs import (
    router as dpm_run_support_router,
)
from src.api.routers.proposals import router as proposal_lifecycle_router
from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory_engine import run_proposal_simulation
from src.core.common.canonical import hash_canonical_payload
from src.core.dpm.engine import run_simulation
from src.core.dpm.policy_packs import (
    apply_policy_pack_to_engine_options,
    resolve_policy_pack_definition,
    resolve_policy_pack_replay_enabled,
)
from src.core.dpm_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationStatusResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
    BatchScenarioMetric,
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    Money,
    PortfolioSnapshot,
    ProposalResult,
    ProposalSimulateRequest,
    RebalanceResult,
    ShelfEntry,
)


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    validate_persistence_profile_guardrails()
    yield


app = FastAPI(
    title="Private Banking Rebalance API",
    version="0.1.0",
    description=(
        "Deterministic rebalance simulation service.\n\n"
        "Domain outcomes for valid payloads are returned in response body status: "
        "`READY`, `PENDING_REVIEW`, or `BLOCKED`."
    ),
    openapi_tags=[
        {
            "name": "DPM Simulation",
            "description": "Core deterministic DPM simulation endpoints.",
        },
        {
            "name": "DPM What-If Analysis",
            "description": "Batch scenario analysis endpoints (sync and async).",
        },
        {
            "name": "DPM Run Supportability",
            "description": "Run, operation, idempotency, and artifact retrieval endpoints.",
        },
        {
            "name": "Advisory Simulation",
            "description": "Advisory proposal simulation and artifact endpoints.",
        },
        {
            "name": "Advisory Proposal Lifecycle",
            "description": "Advisory proposal persistence, workflow, and support endpoints.",
        },
    ],
    lifespan=_app_lifespan,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DPM_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, Dict]]" = OrderedDict()
DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE = 1000
MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE = 1000
PROPOSAL_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, Dict]]" = OrderedDict()

app.include_router(proposal_lifecycle_router)
app.include_router(dpm_run_support_router)
app.include_router(dpm_policy_pack_router)


async def get_db_session():
    """Stub for Database Session (RFC-0005).
    To be replaced with actual AsyncPG session."""
    yield None


@app.exception_handler(Exception)
async def unhandled_exception_to_problem_details(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while serving request", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
            "instance": str(request.url.path),
        },
    )


class RebalanceRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_1",
                    "base_currency": "USD",
                    "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
                    "cash_balances": [{"currency": "USD", "amount": "5000"}],
                },
                "market_data_snapshot": {
                    "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                    "fx_rates": [],
                },
                "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.6"}]},
                "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
                "options": {
                    "target_method": "HEURISTIC",
                    "enable_tax_awareness": False,
                    "enable_settlement_awareness": False,
                },
            }
        }
    }

    portfolio_snapshot: PortfolioSnapshot = Field(
        description="Current portfolio holdings and cash balances."
    )
    market_data_snapshot: MarketDataSnapshot = Field(
        description="Price and FX snapshot used for valuation and intent generation."
    )
    model_portfolio: ModelPortfolio = Field(description="Target model weights by instrument.")
    shelf_entries: List[ShelfEntry] = Field(
        description=(
            "Instrument eligibility and policy metadata (status, attributes, settlement days)."
        )
    )
    options: EngineOptions = Field(description="Request-level engine behavior and feature toggles.")


SIMULATE_READY_EXAMPLE = {
    "summary": "Ready run",
    "value": {
        "status": "READY",
        "rebalance_run_id": "rr_demo1234",
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
    },
}
SIMULATE_PENDING_EXAMPLE = {
    "summary": "Pending review run",
    "value": {
        "status": "PENDING_REVIEW",
        "rebalance_run_id": "rr_demo5678",
        "diagnostics": {"warnings": ["CAPPED_BY_GROUP_LIMIT_sector:TECH"]},
    },
}
SIMULATE_BLOCKED_EXAMPLE = {
    "summary": "Blocked run",
    "value": {
        "status": "BLOCKED",
        "rebalance_run_id": "rr_demo9999",
        "diagnostics": {"warnings": ["OVERDRAFT_ON_T_PLUS_1"]},
    },
}
SIMULATE_409_EXAMPLE = {
    "summary": "Idempotency hash conflict",
    "value": {"detail": "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"},
}

BATCH_EXAMPLE = {
    "summary": "Batch what-if request",
    "value": {
        "portfolio_snapshot": {
            "portfolio_id": "pf_batch",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "0.5"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "scenarios": {
            "baseline": {"options": {}},
            "solver_case": {"options": {"target_method": "SOLVER"}},
        },
    },
}

ANALYZE_RESPONSE_EXAMPLE = {
    "summary": "Batch result",
    "value": {
        "batch_run_id": "batch_ab12cd34",
        "run_at_utc": "2026-02-18T10:00:00+00:00",
        "base_snapshot_ids": {"portfolio_snapshot_id": "pf_batch", "market_data_snapshot_id": "md"},
        "results": {},
        "comparison_metrics": {},
        "failed_scenarios": {},
        "warnings": [],
    },
}
ANALYZE_ASYNC_ACCEPTED_EXAMPLE = {
    "summary": "Async batch accepted",
    "value": {
        "operation_id": "dop_abc12345",
        "operation_type": "ANALYZE_SCENARIOS",
        "status": "PENDING",
        "correlation_id": "corr-batch-async-1",
        "created_at": "2026-02-20T12:00:00+00:00",
        "status_url": "/rebalance/operations/dop_abc12345",
    },
}

PROPOSAL_READY_EXAMPLE = {
    "summary": "Proposal simulation ready",
    "value": {
        "status": "READY",
        "proposal_run_id": "pr_demo1234",
        "correlation_id": "corr_demo1234",
        "intents": [
            {"intent_type": "CASH_FLOW", "currency": "USD", "amount": "2000.00"},
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_GROWTH",
                "quantity": "40",
            },
        ],
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
    },
}

PROPOSAL_PENDING_EXAMPLE = {
    "summary": "Proposal simulation pending review",
    "value": {
        "status": "PENDING_REVIEW",
        "proposal_run_id": "pr_demo5678",
        "correlation_id": "corr_demo5678",
        "diagnostics": {"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}},
        "rule_results": [{"rule_id": "CASH_BAND", "severity": "SOFT", "status": "FAIL"}],
    },
}

PROPOSAL_BLOCKED_EXAMPLE = {
    "summary": "Proposal simulation blocked",
    "value": {
        "status": "BLOCKED",
        "proposal_run_id": "pr_demo9999",
        "correlation_id": "corr_demo9999",
        "diagnostics": {
            "warnings": ["PROPOSAL_WITHDRAWAL_NEGATIVE_CASH"],
            "data_quality": {"price_missing": [], "fx_missing": []},
        },
    },
}

PROPOSAL_409_EXAMPLE = {
    "summary": "Idempotency hash conflict",
    "value": {"detail": "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"},
}


def _resolve_base_snapshot_ids(request: BatchRebalanceRequest) -> Dict[str, str]:
    return {
        "portfolio_snapshot_id": (
            request.portfolio_snapshot.snapshot_id or request.portfolio_snapshot.portfolio_id
        ),
        "market_data_snapshot_id": request.market_data_snapshot.snapshot_id or "md",
    }


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


def _resolve_async_execution_mode() -> str:
    value = os.getenv("DPM_ASYNC_EXECUTION_MODE", "INLINE")
    normalized = value.strip().upper()
    if normalized in {"INLINE", "ACCEPT_ONLY"}:
        return normalized
    return "INLINE"


def _async_manual_execution_enabled() -> bool:
    return _env_flag("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", True)


def _to_invalid_options_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    return f"INVALID_OPTIONS: {first_error.get('msg', 'validation failed')}"


def _build_comparison_metric(
    scenario_result: RebalanceResult,
    base_currency: str,
) -> BatchScenarioMetric:
    security_intents = [
        intent for intent in scenario_result.intents if intent.intent_type == "SECURITY_TRADE"
    ]
    turnover_proxy = sum(
        (
            intent.notional_base.amount
            for intent in security_intents
            if intent.notional_base is not None
        ),
        Decimal("0"),
    )
    return BatchScenarioMetric(
        status=scenario_result.status,
        security_intent_count=len(security_intents),
        gross_turnover_notional_base=Money(amount=turnover_proxy, currency=base_currency),
    )


@app.post(
    "/rebalance/simulate",
    response_model=RebalanceResult,
    status_code=status.HTTP_200_OK,
    tags=["DPM Simulation"],
    summary="Simulate a Portfolio Rebalance",
    description=(
        "Runs one deterministic rebalance simulation.\n\n"
        "Required header: `Idempotency-Key`.\n"
        "Optional header: `X-Correlation-Id`.\n\n"
        "For valid payloads, domain outcomes are returned in the response body status field."
    ),
    responses={
        200: {
            "description": "Simulation completed with domain status in payload.",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": SIMULATE_READY_EXAMPLE,
                        "pending_review": SIMULATE_PENDING_EXAMPLE,
                        "blocked": SIMULATE_BLOCKED_EXAMPLE,
                    }
                }
            },
        },
        422: {
            "description": "Validation error (invalid payload or missing required headers).",
        },
        409: {
            "description": "Idempotency key reused with different canonical request hash.",
            "content": {"application/json": {"examples": {"conflict": SIMULATE_409_EXAMPLE}}},
        },
    },
)
def simulate_rebalance(
    request: RebalanceRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency token for request deduplication at client boundary.",
            examples=["demo-idem-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional trace/correlation identifier propagated to logs.",
            examples=["corr-1234-abcd"],
        ),
    ] = None,
    policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> RebalanceResult:
    """Core DPM simulation endpoint with optional idempotent replay semantics."""
    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    logger.info(
        f"Simulating rebalance. CID={resolved_correlation_id} Idempotency={idempotency_key}"
    )
    default_replay_enabled = _env_flag("DPM_IDEMPOTENCY_REPLAY_ENABLED", True)
    max_size = _env_int("DPM_IDEMPOTENCY_CACHE_MAX_SIZE", DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE)
    request_payload = request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )
    policy_pack_definition = resolve_policy_pack_definition(
        resolution=policy_pack,
        catalog=load_dpm_policy_pack_catalog(),
    )
    effective_options = apply_policy_pack_to_engine_options(
        options=request.options,
        policy_pack=policy_pack_definition,
    )
    replay_enabled = resolve_policy_pack_replay_enabled(
        default_replay_enabled=default_replay_enabled,
        policy_pack=policy_pack_definition,
    )
    logger.debug(
        "Resolved DPM policy pack for simulate. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )

    if replay_enabled:
        existing = DPM_IDEMPOTENCY_CACHE.get(idempotency_key)
        if existing and existing["request_hash"] != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="IDEMPOTENCY_KEY_CONFLICT: request hash mismatch",
            )
        if existing:
            DPM_IDEMPOTENCY_CACHE.move_to_end(idempotency_key)
            return RebalanceResult.model_validate(existing["response"])

    result = run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=effective_options,
        request_hash=request_hash,
        correlation_id=resolved_correlation_id,
    )

    if replay_enabled:
        DPM_IDEMPOTENCY_CACHE[idempotency_key] = {
            "request_hash": request_hash,
            "response": result.model_dump(mode="json"),
        }
        DPM_IDEMPOTENCY_CACHE.move_to_end(idempotency_key)
        while len(DPM_IDEMPOTENCY_CACHE) > max_size:
            DPM_IDEMPOTENCY_CACHE.popitem(last=False)

    try:
        record_dpm_run_for_support(
            result=result,
            request_hash=request_hash,
            portfolio_id=request.portfolio_snapshot.portfolio_id,
            idempotency_key=idempotency_key,
        )
    except Exception:
        logger.exception(
            "Supportability persistence failed. RunID=%s CorrelationID=%s",
            result.rebalance_run_id,
            result.correlation_id,
        )

    if result.status == "BLOCKED":
        logger.warning(f"Run blocked. Diagnostics: {result.diagnostics}")

    return result


@app.post(
    "/rebalance/analyze",
    response_model=BatchRebalanceResult,
    status_code=status.HTTP_200_OK,
    tags=["DPM What-If Analysis"],
    summary="Analyze Multiple Rebalance Scenarios",
    description=(
        "Runs multiple named what-if scenarios using shared snapshots.\n\n"
        "Each scenario validates `options` independently and executes in sorted scenario-key order."
    ),
    responses={
        200: {
            "description": "Batch analysis result.",
            "content": {
                "application/json": {"examples": {"batch_result": ANALYZE_RESPONSE_EXAMPLE}}
            },
        },
        422: {
            "description": "Validation error (invalid shared payload or scenario key format).",
        },
    },
)
def analyze_scenarios(
    request: Annotated[
        BatchRebalanceRequest,
        Field(description="Shared snapshots plus scenario map of option overrides."),
    ],
    correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
    policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "scenario engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> BatchRebalanceResult:
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )
    logger.debug(
        "Resolved DPM policy pack for analyze. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )
    return _execute_batch_analysis(
        request=request,
        correlation_id=correlation_id,
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=None,
        tenant_id=tenant_id,
    )


@app.post(
    "/rebalance/analyze/async",
    response_model=DpmAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["DPM What-If Analysis"],
    summary="Analyze Multiple Rebalance Scenarios Asynchronously",
    description=(
        "Accepts named what-if scenarios for asynchronous execution.\n\n"
        "Execution mode is controlled by `DPM_ASYNC_EXECUTION_MODE` (`INLINE` or `ACCEPT_ONLY`).\n"
        "Use `GET /rebalance/operations/{operation_id}` or "
        "`GET /rebalance/operations/by-correlation/{correlation_id}` for status/result retrieval."
    ),
    responses={
        202: {
            "description": "Async batch accepted.",
            "headers": {
                "X-Correlation-Id": {
                    "description": (
                        "Resolved correlation id for this asynchronous operation "
                        "(client-provided or generated)."
                    ),
                    "schema": {
                        "type": "string",
                        "examples": ["corr-batch-async-1"],
                    },
                }
            },
            "content": {
                "application/json": {"examples": {"accepted": ANALYZE_ASYNC_ACCEPTED_EXAMPLE}}
            },
        },
        404: {"description": "Async operations disabled by configuration."},
        422: {"description": "Validation error (invalid shared payload or scenario key format)."},
    },
)
def analyze_scenarios_async(
    request: Annotated[
        BatchRebalanceRequest,
        Field(description="Shared snapshots plus scenario map of option overrides."),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation identifier for async tracking and lookup.",
            examples=["corr-batch-async-1"],
        ),
    ] = None,
    policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description=(
                "Optional policy-pack identifier for request-scoped policy selection. "
                "When selected and found in catalog, configured policy fields can override "
                "scenario engine options for this request."
            ),
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
    response: Response = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> DpmAsyncAcceptedResponse:
    if not _env_flag("DPM_ASYNC_OPERATIONS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_OPERATIONS_DISABLED",
        )
    service = get_dpm_run_support_service()
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )
    logger.debug(
        "Resolved DPM policy pack for analyze async. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )
    accepted = service.submit_analyze_async(
        correlation_id=correlation_id,
        request_json={
            "batch_request": request.model_dump(mode="json"),
            "policy_context": {
                "request_policy_pack_id": policy_pack_id,
                "tenant_default_policy_pack_id": None,
                "tenant_id": tenant_id,
            },
        },
    )
    if response is not None:
        response.headers["X-Correlation-Id"] = accepted.correlation_id
    if _resolve_async_execution_mode() == "ACCEPT_ONLY":
        return accepted
    _run_analyze_async_operation(operation_id=accepted.operation_id, service=service)
    return accepted


@app.post(
    "/rebalance/operations/{operation_id}/execute",
    response_model=DpmAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["DPM Run Supportability"],
    summary="Execute Pending DPM Async Operation",
    description=(
        "Executes one pending asynchronous DPM analyze operation. "
        "Intended for orchestrated `ACCEPT_ONLY` mode flows."
    ),
    responses={
        200: {"description": "Operation execution completed; returns terminal status payload."},
        404: {"description": "Operation not found or manual execution disabled."},
        409: {"description": "Operation is not in executable pending state."},
    },
)
def execute_dpm_async_operation(
    operation_id: Annotated[
        str,
        Path(description="Asynchronous operation identifier.", examples=["dop_001"]),
    ],
    service: Annotated[DpmRunSupportService, Depends(get_dpm_run_support_service)],
) -> DpmAsyncOperationStatusResponse:
    if not _env_flag("DPM_ASYNC_OPERATIONS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_OPERATIONS_DISABLED",
        )
    if not _async_manual_execution_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_MANUAL_EXECUTION_DISABLED",
        )
    try:
        _run_analyze_async_operation(operation_id=operation_id, service=service)
    except DpmRunNotFoundError as exc:
        detail = str(exc)
        if detail == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    return service.get_async_operation(operation_id=operation_id)


def _execute_batch_analysis(
    *,
    request: BatchRebalanceRequest,
    correlation_id: Optional[str],
    request_policy_pack_id: Optional[str] = None,
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> BatchRebalanceResult:
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    logger.info(f"Analyzing scenario batch. CID={correlation_id} BatchID={batch_id}")

    results = {}
    comparison_metrics = {}
    failed_scenarios = {}
    warnings = []
    policy_resolution = resolve_dpm_policy_pack(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    policy_definition = resolve_policy_pack_definition(
        resolution=policy_resolution,
        catalog=load_dpm_policy_pack_catalog(),
    )

    for scenario_name in sorted(request.scenarios.keys()):
        scenario = request.scenarios[scenario_name]
        try:
            options = EngineOptions.model_validate(scenario.options)
        except ValidationError as exc:
            failed_scenarios[scenario_name] = _to_invalid_options_error(exc)
            continue

        try:
            effective_options = apply_policy_pack_to_engine_options(
                options=options,
                policy_pack=policy_definition,
            )
            scenario_correlation_id = (
                f"{correlation_id}:{scenario_name}"
                if correlation_id
                else f"{batch_id}:{scenario_name}"
            )
            scenario_result = run_simulation(
                portfolio=request.portfolio_snapshot,
                market_data=request.market_data_snapshot,
                model=request.model_portfolio,
                shelf=request.shelf_entries,
                options=effective_options,
                request_hash=f"{batch_id}:{scenario_name}",
                correlation_id=scenario_correlation_id,
            )
            record_dpm_run_for_support(
                result=scenario_result,
                request_hash=f"{batch_id}:{scenario_name}",
                portfolio_id=request.portfolio_snapshot.portfolio_id,
                idempotency_key=None,
            )
            results[scenario_name] = scenario_result
            comparison_metrics[scenario_name] = _build_comparison_metric(
                scenario_result=scenario_result,
                base_currency=request.portfolio_snapshot.base_currency,
            )
        except Exception as exc:
            logger.exception("Scenario execution failed. Scenario=%s", scenario_name)
            failed_scenarios[scenario_name] = f"SCENARIO_EXECUTION_ERROR: {type(exc).__name__}"

    if failed_scenarios:
        warnings.append("PARTIAL_BATCH_FAILURE")

    return BatchRebalanceResult(
        batch_run_id=batch_id,
        run_at_utc=datetime.now(timezone.utc).isoformat(),
        base_snapshot_ids=_resolve_base_snapshot_ids(request),
        results=results,
        comparison_metrics=comparison_metrics,
        failed_scenarios=failed_scenarios,
        warnings=warnings,
    )


def _run_analyze_async_operation(*, operation_id: str, service: DpmRunSupportService) -> None:
    request_json, operation_correlation_id = service.prepare_analyze_operation_execution(
        operation_id=operation_id
    )
    try:
        if isinstance(request_json, dict) and "batch_request" in request_json:
            batch_payload = request_json.get("batch_request") or {}
            policy_context = request_json.get("policy_context") or {}
            request_policy_pack_id = policy_context.get("request_policy_pack_id")
            tenant_default_policy_pack_id = policy_context.get("tenant_default_policy_pack_id")
            tenant_id = policy_context.get("tenant_id")
        else:
            batch_payload = request_json
            request_policy_pack_id = None
            tenant_default_policy_pack_id = None
            tenant_id = None
        batch_request = BatchRebalanceRequest.model_validate(batch_payload)
        result = _execute_batch_analysis(
            request=batch_request,
            correlation_id=operation_correlation_id,
            request_policy_pack_id=request_policy_pack_id,
            tenant_default_policy_pack_id=tenant_default_policy_pack_id,
            tenant_id=tenant_id,
        )
        service.complete_operation_success(
            operation_id=operation_id,
            result_json=result.model_dump(mode="json"),
        )
    except Exception as exc:
        logger.exception("Asynchronous batch analysis failed. OperationID=%s", operation_id)
        service.complete_operation_failure(
            operation_id=operation_id,
            code=type(exc).__name__,
            message=str(exc),
        )


@app.post(
    "/rebalance/proposals/simulate",
    response_model=ProposalResult,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Simulation"],
    summary="Simulate an Advisory Proposal",
    description=(
        "Runs deterministic advisory proposal simulation from advisor-entered cash flows "
        "and manual security trades.\n\n"
        "Processing order:\n"
        "1) Cash flows (if `proposal_apply_cash_flows_first=true`)\n"
        "2) Manual security sells (instrument ascending)\n"
        "3) Manual security buys (instrument ascending)\n\n"
        "Required header: `Idempotency-Key`.\n"
        "Optional header: `X-Correlation-Id` (auto-generated when omitted).\n\n"
        "Requires `options.enable_proposal_simulation=true`."
    ),
    responses={
        200: {
            "description": "Proposal simulation completed with domain status in payload.",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": PROPOSAL_READY_EXAMPLE,
                        "pending_review": PROPOSAL_PENDING_EXAMPLE,
                        "blocked": PROPOSAL_BLOCKED_EXAMPLE,
                    }
                }
            },
        },
        409: {
            "description": "Idempotency key reused with different canonical request hash.",
            "content": {"application/json": {"examples": {"conflict": PROPOSAL_409_EXAMPLE}}},
        },
        422: {"description": "Validation error (invalid payload or missing required headers)."},
    },
)
def simulate_proposal(
    request: ProposalSimulateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key used for dedupe and hash conflict detection.",
            examples=["proposal-idem-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional trace/correlation identifier propagated to logs and response.",
            examples=["corr-proposal-1234"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> ProposalResult:
    return _simulate_proposal_response(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )


def _simulate_proposal_response(
    *,
    request: ProposalSimulateRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
) -> ProposalResult:
    if not request.options.enable_proposal_simulation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true",
        )

    request_payload = request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)

    existing = PROPOSAL_IDEMPOTENCY_CACHE.get(idempotency_key)
    if existing and existing["request_hash"] != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="IDEMPOTENCY_KEY_CONFLICT: request hash mismatch",
        )
    if existing:
        PROPOSAL_IDEMPOTENCY_CACHE.move_to_end(idempotency_key)
        return ProposalResult.model_validate(existing["response"])

    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=resolved_correlation_id,
    )

    PROPOSAL_IDEMPOTENCY_CACHE[idempotency_key] = {
        "request_hash": request_hash,
        "response": result.model_dump(mode="json"),
    }
    PROPOSAL_IDEMPOTENCY_CACHE.move_to_end(idempotency_key)
    while len(PROPOSAL_IDEMPOTENCY_CACHE) > MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE:
        PROPOSAL_IDEMPOTENCY_CACHE.popitem(last=False)
    return result


@app.post(
    "/rebalance/proposals/artifact",
    response_model=ProposalArtifact,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Simulation"],
    summary="Build Advisory Proposal Artifact",
    description=(
        "Runs advisory proposal simulation and returns a deterministic "
        "proposal artifact package.\n\n"
        "Required header: `Idempotency-Key`.\n"
        "Optional header: `X-Correlation-Id` (auto-generated when omitted).\n\n"
        "Requires `options.enable_proposal_simulation=true`."
    ),
    responses={
        200: {"description": "Proposal artifact generated successfully."},
        409: {
            "description": "Idempotency key reused with different canonical request hash.",
            "content": {"application/json": {"examples": {"conflict": PROPOSAL_409_EXAMPLE}}},
        },
        422: {"description": "Validation error (invalid payload or missing required headers)."},
    },
)
def build_proposal_artifact_endpoint(
    request: ProposalSimulateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key used for dedupe and hash conflict detection.",
            examples=["proposal-artifact-idem-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional trace/correlation identifier propagated to logs and response.",
            examples=["corr-proposal-artifact-1234"],
        ),
    ] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> ProposalArtifact:
    proposal_result = _simulate_proposal_response(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    return build_proposal_artifact(request=request, proposal_result=proposal_result)
