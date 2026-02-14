import hashlib
import json
from typing import Dict, List, Optional

from fastapi import FastAPI, Header
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

app = FastAPI(title="DPM Rebalance Simulation API (RFC-0003)")

MOCK_DB_RUNS: Dict[str, dict] = {}
MOCK_DB_IDEMPOTENCY: Dict[str, str] = {}


class RebalanceRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    options: EngineOptions


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/rebalance/simulate", response_model=RebalanceResult)
async def simulate_rebalance(
    payload: RebalanceRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    payload_json_str = payload.model_dump_json(exclude_none=True)
    request_hash = f"sha256:{hashlib.sha256(payload_json_str.encode('utf-8')).hexdigest()}"
    correlation_id = x_correlation_id or "c_generated_uuid"

    if idempotency_key in MOCK_DB_IDEMPOTENCY:
        if MOCK_DB_IDEMPOTENCY[idempotency_key] != request_hash:
            return JSONResponse(
                status_code=409,
                content={
                    "type": "https://api.bank.com/errors/idempotency/conflict",
                    "title": "Idempotency Key Conflict",
                    "status": 409,
                    "error_code": "IDEMPOTENCY_CONFLICT",
                    "detail": "Key used with a different request payload.",
                    "correlation_id": correlation_id,
                },
            )
        for run_data in MOCK_DB_RUNS.values():
            if run_data["lineage"]["request_hash"] == request_hash:
                return run_data

    result = run_simulation(
        portfolio=payload.portfolio_snapshot,
        market_data=payload.market_data_snapshot,
        model=payload.model_portfolio,
        shelf=payload.shelf_entries,
        options=payload.options,
        request_hash=request_hash,
    )
    result.correlation_id = correlation_id
    result_dict = json.loads(result.model_dump_json())
    MOCK_DB_RUNS[result.rebalance_run_id] = result_dict
    MOCK_DB_IDEMPOTENCY[idempotency_key] = request_hash

    return result
