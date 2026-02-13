import hashlib
import json
from typing import Dict, List, Optional

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    RebalanceResult,
    ShelfEntry,
)

app = FastAPI(title="DPM Rebalance Simulation API (RFC-0002)")

# --- Mock Database for MVP Persistence ---
# In a production system, this would be a PostgreSQL repository.
MOCK_DB_RUNS: Dict[str, dict] = {}
MOCK_DB_IDEMPOTENCY: Dict[str, str] = {}  # idempotency_key -> request_hash


class RebalanceRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    options: EngineOptions


# --- Error Handlers (RFC 7807 Problem Details) ---
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Maps domain logic exceptions into RFC 7807 Problem Details payloads."""
    error_msg = str(exc)

    if "CONSTRAINT_INFEASIBLE" in error_msg:
        code = "CONSTRAINT_INFEASIBLE"
    elif "Missing price" in error_msg or "Missing FX" in error_msg:
        code = "DATA_QUALITY_ERROR"
    else:
        code = "UNPROCESSABLE_DOMAIN_ERROR"

    problem_details = {
        "type": f"https://api.bank.com/errors/rebalance/{code.lower()}",
        "title": "Domain Validation Failed",
        "status": 422,
        "error_code": code,
        "detail": error_msg,
        "instance": request.url.path,
        "correlation_id": request.headers.get("x-correlation-id", "unknown"),
    }
    return JSONResponse(status_code=422, content=problem_details)


@app.get("/health")
def health_check():
    return {"status": "UP", "version": "1.1.0-rfc0002"}


@app.post("/rebalance/simulate", response_model=RebalanceResult)
async def simulate_rebalance(
    payload: RebalanceRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    """
    Simulates a portfolio rebalance. Enforces idempotency via request hashing.
    """
    # 1. Compute Cryptographic Request Hash
    payload_json_str = payload.model_dump_json(exclude_none=True)
    request_hash = f"sha256:{hashlib.sha256(payload_json_str.encode('utf-8')).hexdigest()}"

    correlation_id = x_correlation_id or "c_generated_uuid"

    # 2. Idempotency Check
    if idempotency_key in MOCK_DB_IDEMPOTENCY:
        cached_hash = MOCK_DB_IDEMPOTENCY[idempotency_key]
        if cached_hash != request_hash:
            # Hash mismatch means they reused the key for a different request
            problem = {
                "type": "https://api.bank.com/errors/idempotency/conflict",
                "title": "Idempotency Key Conflict",
                "status": 409,
                "error_code": "IDEMPOTENCY_CONFLICT",
                "detail": (
                    "The provided Idempotency-Key was previously "
                    "used with a different request payload."
                ),
                "correlation_id": correlation_id,
            }
            return JSONResponse(status_code=409, content=problem)

        # Cache Hit - Exact Match. Return the persisted run.
        # We search the runs DB to find the one matching this hash.
        for run_id, run_data in MOCK_DB_RUNS.items():
            if run_data["lineage"]["request_hash"] == request_hash:
                return run_data

    # 3. Cache Miss - Execute Core Domain Logic
    result = run_simulation(
        portfolio=payload.portfolio_snapshot,
        market_data=payload.market_data_snapshot,
        model=payload.model_portfolio,
        shelf=payload.shelf_entries,
        options=payload.options,
        request_hash=request_hash,
    )

    # Inject the operational correlation ID
    result.correlation_id = correlation_id

    # 4. Persistence
    result_dict = json.loads(result.model_dump_json())
    MOCK_DB_RUNS[result.rebalance_run_id] = result_dict
    MOCK_DB_IDEMPOTENCY[idempotency_key] = request_hash

    return result
