"""FILE: src/api/main.py"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from src.api.enterprise_readiness import (
    build_enterprise_audit_middleware,
    validate_enterprise_runtime_config,
)
from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.observability import correlation_id_var, setup_observability
from src.api.openapi_enrichment import enrich_openapi_schema
from src.api.proposals.router import (
    ensure_proposal_runtime_ready,
    recover_proposal_async_runtime,
)
from src.api.proposals.router import (
    router as proposal_lifecycle_router,
)
from src.api.routers.advisory_simulation import (
    build_proposal_artifact_endpoint,
    simulate_proposal,
)
from src.api.routers.advisory_simulation import (
    router as advisory_simulation_router,
)
from src.api.routers.bank_demo_proof import router as bank_demo_proof_router
from src.api.routers.integration_capabilities import (
    router as integration_capabilities_router,
)
from src.api.routers.tactical_house_view import router as tactical_house_view_router
from src.api.runtime_persistence import validate_advisory_runtime_persistence
from src.api.sensitive_error_details import contains_sensitive_error_detail
from src.api.services.advisory_simulation_service import (
    simulate_proposal_response as _simulate_proposal_response,
)
from src.api.workspaces.router import router as workspace_router
from src.core.advisory_engine import run_proposal_simulation
from src.core.workspace.models import WorkspaceStatefulInput
from src.integrations.lotus_core import LotusCoreSimulationUnavailableError
from src.integrations.lotus_core.context_resolution import LotusCoreResolvedAdvisoryContext
from src.integrations.lotus_core.stateful_context import resolve_stateful_context_with_lotus_core


@asynccontextmanager
async def _app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    validate_advisory_runtime_persistence()
    ensure_proposal_runtime_ready()
    recover_proposal_async_runtime()
    yield


app = FastAPI(
    title="Lotus Advise API",
    version="0.1.0",
    description="Advisor-led proposal simulation and lifecycle service.",
    lifespan=_app_lifespan,
    openapi_tags=[
        {
            "name": "Advisory Simulation",
            "description": (
                "Core advisory proposal simulation endpoints used to evaluate a proposed set of "
                "portfolio actions and generate deterministic proposal evidence."
            ),
        },
        {
            "name": "Advisory Proposal Lifecycle",
            "description": (
                "Persisted advisory proposal workflow endpoints covering creation, versioning, "
                "state transitions, approvals, report requests, and execution handoff."
            ),
        },
        {
            "name": "Advisory Proposal Memo",
            "description": (
                "RFC-0024 advisor proposal memo endpoints for persisted memo evidence packs, "
                "projection posture, review events, report-package lineage, memo lineage, and "
                "replay evidence. Gateway, Workbench, and advisor-use report/render/archive "
                "support are available with client-ready memo publication gated."
            ),
        },
        {
            "name": "Advisory Policy Evaluation",
            "description": (
                "RFC-0025 certified Advise API endpoints for policy evaluation records, replay, "
                "review queues, lineage, append-only review/sign-off/report reference events, and "
                "sign-off source packages. Gateway, Workbench, and advisor/compliance report "
                "realization are available with client-ready publication gated."
            ),
        },
        {
            "name": "Advisor Cockpit",
            "description": (
                "RFC-0026 Advise-owned cockpit APIs for source-backed action lists, snapshots, "
                "supportability posture, idempotent acknowledgement, active cockpit data-product "
                "posture, and Gateway/Workbench canonical proof. Client-ready publication, "
                "external client communication, CRM system-of-record behavior, OMS order "
                "lifecycle, and completed policy approval authority remain gated."
            ),
        },
        {
            "name": "Advisory Copilot",
            "description": (
                "RFC-0027 Advise-owned governed advisory copilot APIs for bounded evidence "
                "packets, workflow-pack-backed actions, run retrieval, review audit, proposal "
                "version run lookup, Gateway/Workbench consumption, data-product support, "
                "canonical proof, and supportability posture. Client-ready publication remains "
                "gated."
            ),
        },
        {
            "name": "Bank Demo Proof",
            "description": (
                "RFC-0028 source-owned bank-demo proof APIs for scenario contracts, "
                "supported-claim governance, and sanitized proof-pack capture. These APIs do "
                "not approve client-ready publication, external client communication, OMS order "
                "lifecycle, or RFP/security claims."
            ),
        },
        {
            "name": "Advisory Operations & Support",
            "description": (
                "Operational lookup and investigation endpoints for async status, workflow "
                "history, lineage, approval history, idempotency tracing, and execution support."
            ),
        },
        {
            "name": "Advisory Workspace",
            "description": (
                "Workspace-oriented drafting endpoints for iterative advisory preparation before "
                "formal proposal lifecycle ownership begins."
            ),
        },
        {
            "name": "Integration",
            "description": (
                "Platform-facing service capability and contract discovery endpoints used by "
                "other Lotus services and orchestration layers."
            ),
        },
        {
            "name": "Tactical House View",
            "description": (
                "Source-owned advisory cohort endpoints for governed tactical house-view "
                "affected-portfolio evaluation."
            ),
        },
        {
            "name": "Health",
            "description": (
                "Operational liveness and readiness probes for runtime health verification."
            ),
        },
        {
            "name": "Monitoring",
            "description": (
                "Operational telemetry endpoints for metrics scraping and observability tooling."
            ),
        },
    ],
)

logger = logging.getLogger(__name__)
LOTUS_CORE_SIMULATION_UNAVAILABLE_DETAIL = "LOTUS_CORE_SIMULATION_UNAVAILABLE"
READINESS_CHECK_FAILED_DETAIL = "READINESS_CHECK_FAILED"
setup_observability(app)
validate_enterprise_runtime_config()
app.middleware("http")(build_enterprise_audit_middleware())

app.include_router(proposal_lifecycle_router)
app.include_router(advisory_simulation_router)
app.include_router(bank_demo_proof_router)
app.include_router(integration_capabilities_router)
app.include_router(tactical_house_view_router)
app.include_router(workspace_router)


def resolve_lotus_core_advisory_context(
    stateful_input: WorkspaceStatefulInput,
) -> LotusCoreResolvedAdvisoryContext:
    return resolve_stateful_context_with_lotus_core(stateful_input)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return cast(dict[str, Any], app.openapi_schema)
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    schema = enrich_openapi_schema(schema, service_name="lotus-advise")
    app.openapi_schema = schema
    return cast(dict[str, Any], app.openapi_schema)


app.openapi = custom_openapi


def _readiness_probe() -> tuple[bool, str | None]:
    try:
        validate_advisory_runtime_persistence()
        ensure_proposal_runtime_ready()
    except RuntimeError as exc:
        return False, _safe_readiness_error_detail(str(exc))
    except (TypeError, ValueError):
        return False, "PROPOSAL_POSTGRES_CONNECTION_FAILED"
    return True, None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
def health_ready() -> JSONResponse:
    ready, detail = _readiness_probe()
    if ready:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Service Unavailable",
            "status": 503,
            "detail": detail or "READINESS_CHECK_FAILED",
            "instance": "/health/ready",
            "correlation_id": correlation_id_var.get() or "",
        },
    )


def _safe_request_validation_errors(
    errors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    safe_errors: list[dict[str, Any]] = []
    for error in errors:
        safe_errors.append(
            {
                "type": error.get("type", "value_error"),
                "loc": error.get("loc", []),
                "msg": error.get("msg", "Invalid request payload."),
            }
        )
    return safe_errors


@app.exception_handler(RequestValidationError)
async def request_validation_error_to_safe_response(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE,
        content={"detail": _safe_request_validation_errors(exc.errors())},
    )


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
            "correlation_id": correlation_id_var.get() or "",
        },
    )


@app.exception_handler(LotusCoreSimulationUnavailableError)
async def lotus_core_simulation_unavailable_to_problem_details(
    request: Request,
    exc: LotusCoreSimulationUnavailableError,
) -> JSONResponse:
    status_code = exc.status_code or status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Upstream Canonical Simulation Error"
            if status_code != status.HTTP_503_SERVICE_UNAVAILABLE
            else "Service Unavailable",
            "status": status_code,
            "detail": _safe_lotus_core_simulation_error_detail(str(exc)),
            "instance": str(request.url.path),
            "correlation_id": correlation_id_var.get() or "",
        },
    )


def _safe_lotus_core_simulation_error_detail(error_detail: str) -> str:
    if not error_detail or contains_sensitive_error_detail(error_detail):
        return LOTUS_CORE_SIMULATION_UNAVAILABLE_DETAIL
    return error_detail


def _safe_readiness_error_detail(error_detail: str) -> str:
    if not error_detail or contains_sensitive_error_detail(error_detail):
        return READINESS_CHECK_FAILED_DETAIL
    return error_detail


__all__ = [
    "_simulate_proposal_response",
    "app",
    "build_proposal_artifact_endpoint",
    "lotus_core_simulation_unavailable_to_problem_details",
    "request_validation_error_to_safe_response",
    "run_proposal_simulation",
    "simulate_proposal",
    "unhandled_exception_to_problem_details",
]
