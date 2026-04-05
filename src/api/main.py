"""FILE: src/api/main.py"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast

from fastapi import FastAPI, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from src.api.dependencies import get_db_session
from src.api.enterprise_readiness import (
    build_enterprise_audit_middleware,
    validate_enterprise_runtime_config,
)
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
from src.api.routers.integration_capabilities import (
    router as integration_capabilities_router,
)
from src.api.runtime_persistence import validate_advisory_runtime_persistence
from src.api.services.advisory_simulation_service import (
    MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE,
    PROPOSAL_IDEMPOTENCY_CACHE,
)
from src.api.services.advisory_simulation_service import (
    simulate_proposal_response as _simulate_proposal_response,
)
from src.api.workspaces.router import router as workspace_router
from src.core.advisory_engine import run_proposal_simulation


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
                "portfolio actions and generate a client-ready artifact."
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
setup_observability(app)
validate_enterprise_runtime_config()
app.middleware("http")(build_enterprise_audit_middleware())

app.include_router(proposal_lifecycle_router)
app.include_router(advisory_simulation_router)
app.include_router(integration_capabilities_router)
app.include_router(workspace_router)


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
        return False, str(exc)
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


__all__ = [
    "MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE",
    "PROPOSAL_IDEMPOTENCY_CACHE",
    "_simulate_proposal_response",
    "app",
    "build_proposal_artifact_endpoint",
    "get_db_session",
    "run_proposal_simulation",
    "simulate_proposal",
    "unhandled_exception_to_problem_details",
]
