from src.core.models import (
    PortfolioSnapshot, MarketDataSnapshot, ModelPortfolio, 
    ShelfEntry, EngineOptions, RebalanceResult
)
from typing import List

def run_simulation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    model: ModelPortfolio,
    shelf: List[ShelfEntry],
    options: EngineOptions
) -> RebalanceResult:
    # TODO: Implement pipeline
    raise NotImplementedError("Engine not yet implemented.")
