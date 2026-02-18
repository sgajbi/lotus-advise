"""
FILE: src/api/main.py
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, status
from pydantic import BaseModel, ValidationError

from src.core.engine import run_simulation
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
    BatchScenarioMetric,
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    Money,
    PortfolioSnapshot,
    RebalanceResult,
    ShelfEntry,
)

app = FastAPI(title="DPM Rebalance Engine", version="0.1.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_db_session():
    """Stub for Database Session (RFC-0005).
    To be replaced with actual AsyncPG session."""
    yield None


class RebalanceRequest(BaseModel):
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    options: EngineOptions


def _resolve_base_snapshot_ids(request: BatchRebalanceRequest) -> Dict[str, str]:
    return {
        "portfolio_snapshot_id": (
            request.portfolio_snapshot.snapshot_id or request.portfolio_snapshot.portfolio_id
        ),
        "market_data_snapshot_id": request.market_data_snapshot.snapshot_id or "md",
    }


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
    summary="Simulate a Portfolio Rebalance",
)
async def simulate_rebalance(
    request: RebalanceRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> RebalanceResult:
    """
    Core calculation endpoint. Stateless domain logic.
    """
    logger.info(f"Simulating rebalance. CID={correlation_id} Idempotency={idempotency_key}")

    result = run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=request.options,
        request_hash=idempotency_key,
    )

    if result.status == "BLOCKED":
        logger.warning(f"Run blocked. Diagnostics: {result.diagnostics}")

    return result


@app.post(
    "/rebalance/analyze",
    response_model=BatchRebalanceResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Multiple Rebalance Scenarios",
)
async def analyze_scenarios(
    request: BatchRebalanceRequest,
    correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
    db: Annotated[None, Depends(get_db_session)] = None,
) -> BatchRebalanceResult:
    """
    Batch scenario orchestration endpoint.
    Reuses single-run simulation with shared snapshots and per-scenario options.
    """
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    logger.info(f"Analyzing scenario batch. CID={correlation_id} BatchID={batch_id}")

    results = {}
    comparison_metrics = {}
    failed_scenarios = {}
    warnings = []

    for scenario_name in sorted(request.scenarios.keys()):
        scenario = request.scenarios[scenario_name]
        try:
            options = EngineOptions.model_validate(scenario.options)
        except ValidationError as exc:
            failed_scenarios[scenario_name] = _to_invalid_options_error(exc)
            continue

        try:
            scenario_result = run_simulation(
                portfolio=request.portfolio_snapshot,
                market_data=request.market_data_snapshot,
                model=request.model_portfolio,
                shelf=request.shelf_entries,
                options=options,
                request_hash=f"{batch_id}:{scenario_name}",
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
