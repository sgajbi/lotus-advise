import uuid
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
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

app = FastAPI(
    title="DPM Rebalance Simulation API",
    description="Enterprise Rebalance Engine for Discretionary Portfolio Management",
    version="MVP-1",
)


# Request Model bridging the API to our Core Engine
class SimulateRequest(BaseModel):
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    options: EngineOptions

    # Silence the Pydantic V2 warning for the 'model_' prefix
    model_config = {"protected_namespaces": ()}


@app.post("/rebalance/simulate", response_model=RebalanceResult)
def simulate_rebalance(
    request: SimulateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    correlation_id = x_correlation_id or f"c_{uuid.uuid4().hex[:8]}"

    try:
        result = run_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            model=request.model_portfolio,
            shelf=request.shelf_entries,
            options=request.options,
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "type": "https://api.dpm.com/errors/internal-server-error",
                "title": "Simulation Failed",
                "detail": str(e),
                "correlation_id": correlation_id,
            },
        )


@app.get("/health")
def health_check():
    return {"status": "UP", "version": "MVP-1"}
