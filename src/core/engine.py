from decimal import Decimal
from typing import List
from src.core.models import (
    PortfolioSnapshot, MarketDataSnapshot, ModelPortfolio, 
    ShelfEntry, EngineOptions, RebalanceResult, OrderIntent, Money
)

def run_simulation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    model: ModelPortfolio,
    shelf: List[ShelfEntry],
    options: EngineOptions
) -> RebalanceResult:
    
    # 1. Calculate Total Portfolio Value (Base Currency)
    total_value = Decimal("0.0")
    for cash in portfolio.cash_balances:
        if cash.currency == portfolio.base_currency:
            total_value += cash.amount
    
    # Add existing position market values (omitted in this first pass since positions are empty)
    for pos in portfolio.positions:
        if pos.market_value and pos.market_value.currency == portfolio.base_currency:
            total_value += pos.market_value.amount
            
    intents = []
    
    # 2. Build Targets and Generate Trades
    for target in model.targets:
        # Check Product Shelf
        shelf_entry = next((s for s in shelf if s.instrument_id == target.instrument_id), None)
        if not shelf_entry or shelf_entry.status in ["BANNED", "SUSPENDED"]:
            continue  # Exclude from universe
            
        # Get Price Data
        price_entry = next((p for p in market_data.prices if p.instrument_id == target.instrument_id), None)
        if not price_entry:
            return RebalanceResult(status="BLOCKED", intents=[])  # Data Quality failure
            
        # Calculate Target Value
        target_value = total_value * target.weight
        
        # Calculate Current Value (Assume 0 for now as we have no positions)
        current_value = Decimal("0.0")
        for pos in portfolio.positions:
            if pos.instrument_id == target.instrument_id and pos.market_value:
                current_value = pos.market_value.amount
                
        delta_value = target_value - current_value
        
        # Trade Translator
        if delta_value > 0:  # BUY
            # Round down to nearest whole unit to prevent overdrafts
            qty = int(delta_value // price_entry.price)
            notional = Decimal(qty) * price_entry.price
            
            # Dust Suppression
            if options.suppress_dust_trades and shelf_entry.min_notional:
                if notional < shelf_entry.min_notional.amount:
                    continue  # Skip trade
                    
            if qty > 0:
                intents.append(OrderIntent(
                    action="BUY",
                    instrument_id=target.instrument_id,
                    quantity=Decimal(qty),
                    est_notional=Money(amount=notional, currency=price_entry.currency)
                ))
                
    return RebalanceResult(status="READY", intents=intents)