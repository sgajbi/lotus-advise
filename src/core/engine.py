from decimal import Decimal
from typing import List, Dict
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
    
    for pos in portfolio.positions:
        if pos.market_value and pos.market_value.currency == portfolio.base_currency:
            total_value += pos.market_value.amount
            
    # 2. Filter Universe and Extract Initial Weights
    eligible_targets: Dict[str, Decimal] = {}
    for target in model.targets:
        shelf_entry = next((s for s in shelf if s.instrument_id == target.instrument_id), None)
        if not shelf_entry or shelf_entry.status in ["BANNED", "SUSPENDED"]:
            continue  # Exclude from universe
        eligible_targets[target.instrument_id] = target.weight

    # 3. Apply Single Position Maximum (Single-Pass Redistribution)
    if options.single_position_max_weight is not None:
        max_w = options.single_position_max_weight
        excess_weight = Decimal("0.0")
        capped_instruments = set()
        
        # Identify breaches and cap them
        for instr_id, weight in eligible_targets.items():
            if weight > max_w:
                excess_weight += (weight - max_w)
                eligible_targets[instr_id] = max_w
                capped_instruments.add(instr_id)
        
        # Redistribute excess proportionally to remaining eligible instruments
        if excess_weight > Decimal("0.0"):
            recipients = {k: v for k, v in eligible_targets.items() if k not in capped_instruments}
            total_recipient_weight = sum(recipients.values())
            
            if total_recipient_weight == Decimal("0.0"):
                # No valid recipients available to absorb the excess
                return RebalanceResult(status="BLOCKED", intents=[])
                
            for instr_id, weight in recipients.items():
                proportion = weight / total_recipient_weight
                additional_weight = excess_weight * proportion
                new_weight = weight + additional_weight
                
                # RFC Rule: If recipient breaches max after redistribution, fail the run.
                if new_weight > max_w:
                    return RebalanceResult(status="BLOCKED", intents=[])
                    
                eligible_targets[instr_id] = new_weight

    intents = []
    
    # 4. Generate Trades (Trade Translator)
    for instr_id, target_weight in eligible_targets.items():
        shelf_entry = next((s for s in shelf if s.instrument_id == instr_id), None)
        price_entry = next((p for p in market_data.prices if p.instrument_id == instr_id), None)
        
        if not price_entry:
            return RebalanceResult(status="BLOCKED", intents=[])  # Data Quality failure
            
        target_value = total_value * target_weight
        
        # Calculate Current Value
        current_value = Decimal("0.0")
        for pos in portfolio.positions:
            if pos.instrument_id == instr_id and pos.market_value:
                current_value = pos.market_value.amount
                
        delta_value = target_value - current_value
        
        if delta_value > Decimal("0.0"):  # BUY Action
            # Round down to nearest whole unit
            qty = int(delta_value // price_entry.price)
            notional = Decimal(qty) * price_entry.price
            
            # Dust Suppression
            if options.suppress_dust_trades and shelf_entry and shelf_entry.min_notional:
                if notional < shelf_entry.min_notional.amount:
                    continue  # Skip trade
                    
            if qty > 0:
                intents.append(OrderIntent(
                    action="BUY",
                    instrument_id=instr_id,
                    quantity=Decimal(qty),
                    est_notional=Money(amount=notional, currency=price_entry.currency)
                ))
                
    # 5. Guarantee Deterministic Output Ordering
    intents.sort(key=lambda x: x.instrument_id or "")

    return RebalanceResult(status="READY", intents=intents)