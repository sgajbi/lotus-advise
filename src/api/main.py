"""
FILE: src/api/main.py
"""

import logging
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, Header, Response, status
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

app = FastAPI(title="DPM Rebalance Engine", version="0.1.0")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Dependencies ---
async def get_db_session():
    """Stub for Database Session (RFC-0005). To be replaced with actual AsyncPG session."""
    yield None


# --- Models ---
class RebalanceRequest(BaseModel):
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    options: EngineOptions


# --- Endpoints ---
@app.post(
    "/rebalance/simulate",
    response_model=RebalanceResult,
    status_code=status.HTTP_200_OK,
    summary="Simulate a Portfolio Rebalance",
)
async def simulate_rebalance(
    request: RebalanceRequest,
    response: Response,
    idempotency_key: Annotated[Optional[str], Header(alias="Idempotency-Key")] = None,
    correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> RebalanceResult:
    """
    Core calculation endpoint. Stateless domain logic.
    """
    logger.info(f"Simulating rebalance. CID={correlation_id} Idempotency={idempotency_key}")

    # Run the Domain Engine
    result = run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=request.options,
        request_hash=idempotency_key or "no_key",  # Pass key as hash for lineage
    )

    # Map Domain Status to HTTP Status Codes if needed (RFC-7807)
    # RFC-0003 Spec: "BLOCKED" is a valid 200 OK domain result.
    if result.status == "BLOCKED":
        logger.warning(f"Run blocked. Diagnostics: {result.diagnostics}")

    return result
