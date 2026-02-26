"""FILE: src/api/main.py"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.dependencies import get_db_session
from src.api.enterprise_readiness import (
    build_enterprise_audit_middleware,
    validate_enterprise_runtime_config,
)
from src.api.observability import correlation_id_var, setup_observability
from src.api.persistence_profile import validate_persistence_profile_guardrails
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
from src.api.routers.proposals import router as proposal_lifecycle_router
from src.api.services.advisory_simulation_service import (
    MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE,
    PROPOSAL_IDEMPOTENCY_CACHE,
    run_proposal_simulation,
)
from src.api.services.advisory_simulation_service import (
    simulate_proposal_response as _simulate_proposal_response,
)


@asynccontextmanager
async def _app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    validate_persistence_profile_guardrails()
    yield


app = FastAPI(
    title="Lotus Advise API",
    version="0.1.0",
    description="Advisor-led proposal simulation and lifecycle service.",
    lifespan=_app_lifespan,
)

logger = logging.getLogger(__name__)
setup_observability(app)
validate_enterprise_runtime_config()
app.middleware("http")(build_enterprise_audit_middleware())

app.include_router(proposal_lifecycle_router)
app.include_router(advisory_simulation_router)
app.include_router(integration_capabilities_router)
app.include_router(proposal_lifecycle_router, prefix="/api/v1")
app.include_router(advisory_simulation_router, prefix="/api/v1")
app.include_router(integration_capabilities_router, prefix="/api/v1")


@app.get("/health")
@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
@app.get("/api/v1/health/live")
def health_live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
@app.get("/api/v1/health/ready")
def health_ready() -> dict[str, str]:
    return {"status": "ready"}


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
