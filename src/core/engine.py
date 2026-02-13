from decimal import Decimal
from typing import List, Dict
from src.core.models import (
    PortfolioSnapshot, MarketDataSnapshot, ModelPortfolio, 
    ShelfEntry, EngineOptions, RebalanceResult, OrderIntent, Money
)

def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Decimal:
    """Helper to resolve FX rates. Assumes direct pairs like USD/SGD in MVP."""
    if from_ccy == to_ccy:
        return Decimal("1.0")
    
    pair_name = f"{from_ccy}/{to_ccy}"
    rate_entry = next((fx for fx in market_data.fx_rates if fx.pair == pair_name), None)
    if rate_entry:
        return rate_entry.rate
    
    raise ValueError(f"Missing FX rate for {pair_name}")

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
        rate = get_fx_rate(market_data, cash.currency, portfolio.base_currency)
        total_value += cash.amount * rate
    
    for pos in portfolio.positions:
        if pos.market_value:
            rate = get_fx_rate(market_data, pos.market_value.currency, portfolio.base_currency)
            total_value += pos.market_value.amount * rate
            
    # 2. Filter Universe
    eligible_targets: Dict[str, Decimal] = {}
    for target in model.targets:
        shelf_entry = next((s for s in shelf if s.instrument_id == target.instrument_id), None)
        if not shelf_entry or shelf_entry.status in ["BANNED", "SUSPENDED"]:
            continue
        eligible_targets[target.instrument_id] = target.weight

    # 3. Apply Single Position Maximum
    if options.single_position_max_weight is not None:
        max_w = options.single_position_max_weight
        excess_weight = Decimal("0.0")
        capped_instruments = set()
        
        for instr_id, weight in eligible_targets.items():
            if weight > max_w:
                excess_weight += (weight - max_w)
                eligible_targets[instr_id] = max_w
                capped_instruments.add(instr_id)
        
        if excess_weight > Decimal("0.0"):
            recipients = {k: v for k, v in eligible_targets.items() if k not in capped_instruments}
            total_recipient_weight = sum(recipients.values())
            
            if total_recipient_weight == Decimal("0.0"):
                return RebalanceResult(status="BLOCKED", intents=[])
                
            for instr_id, weight in recipients.items():
                proportion = weight / total_recipient_weight
                new_weight = weight + (excess_weight * proportion)
                if new_weight > max_w:
                    return RebalanceResult(status="BLOCKED", intents=[])
                eligible_targets[instr_id] = new_weight

    intents = []
    required_cash_by_currency: Dict[str, Decimal] = {}
    
    # 4. Generate Trades
    for instr_id, target_weight in eligible_targets.items():
        shelf_entry = next((s for s in shelf if s.instrument_id == instr_id), None)
        price_entry = next((p for p in market_data.prices if p.instrument_id == instr_id), None)
        
        if not price_entry:
            return RebalanceResult(status="BLOCKED", intents=[])
            
        target_value_base = total_value * target_weight
        
        # Convert Target Value to Instrument Currency
        rate_to_base = get_fx_rate(market_data, price_entry.currency, portfolio.base_currency)
        target_value_instr = target_value_base / rate_to_base
        
        current_value_instr = Decimal("0.0")
        for pos in portfolio.positions:
            if pos.instrument_id == instr_id and pos.market_value:
                current_value_instr = pos.market_value.amount
                
        delta_value = target_value_instr - current_value_instr
        
        if delta_value > Decimal("0.0"):
            qty = int(delta_value // price_entry.price)
            notional = Decimal(qty) * price_entry.price
            
            if options.suppress_dust_trades and shelf_entry and shelf_entry.min_notional:
                if notional < shelf_entry.min_notional.amount:
                    continue
                    
            if qty > 0:
                intents.append(OrderIntent(
                    intent_type="SECURITY",
                    action="BUY",
                    instrument_id=instr_id,
                    quantity=Decimal(qty),
                    est_notional=Money(amount=notional, currency=price_entry.currency)
                ))
                # Track required cash for FX generation
                required_cash_by_currency[price_entry.currency] = required_cash_by_currency.get(price_entry.currency, Decimal("0.0")) + notional

    # 5. Generate FX Intents (Hub-and-Spoke)
    for ccy, required_amt in required_cash_by_currency.items():
        if ccy == portfolio.base_currency:
            continue
            
        current_cash = Decimal("0.0")
        for cash in portfolio.cash_balances:
            if cash.currency == ccy:
                current_cash = cash.amount
                
        deficit = required_amt - current_cash
        if deficit > Decimal("0.0"):
            buy_amt = deficit * (Decimal("1.0") + options.fx_buffer_pct)
            rate = get_fx_rate(market_data, ccy, portfolio.base_currency)
            sell_amt = buy_amt * rate
            
            intents.append(OrderIntent(
                intent_type="FX",
                action="FX_BUY",
                currency_pair=f"{ccy}/{portfolio.base_currency}",
                buy_amount=Money(amount=buy_amt, currency=ccy),
                sell_amount=Money(amount=sell_amt, currency=portfolio.base_currency)
            ))
                

# 6. Sort intents for determinism (RFC Rule: SELL -> FX -> BUY)
    def sort_key(intent: OrderIntent):
        if intent.action == "SELL":
            priority = 0
        elif intent.intent_type == "FX":
            priority = 1
        else: # BUY
            priority = 2
            
        sec_id = intent.currency_pair if intent.intent_type == "FX" else intent.instrument_id
        return f"{priority}_{sec_id}"
        
    intents.sort(key=sort_key)

    return RebalanceResult(status="READY", intents=intents)