import uuid
from decimal import Decimal
from typing import Dict, List

from src.core.models import (
    CashBalance,
    DiagnosticsData,
    EngineOptions,
    ExcludedInstrument,
    IntentRationale,
    LineageData,
    MarketDataSnapshot,
    ModelPortfolio,
    Money,
    OrderIntent,
    PortfolioSnapshot,
    RebalanceResult,
    RuleResult,
    ShelfEntry,
    SimulatedState,
    TargetData,
    UniverseCoverage,
    UniverseData,
)


def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Decimal:
    if from_ccy == to_ccy:
        return Decimal("1.0")
    pair_name = f"{from_ccy}/{to_ccy}"
    rate_entry = next((fx for fx in market_data.fx_rates if fx.pair == pair_name), None)
    if rate_entry:
        return rate_entry.rate
    raise ValueError(f"Missing FX rate for {pair_name}")


def calculate_position_value_base(pos, market_data: MarketDataSnapshot, base_ccy: str) -> Decimal:
    if pos.market_value:
        rate = get_fx_rate(market_data, pos.market_value.currency, base_ccy)
        return pos.market_value.amount * rate

    price_entry = next(
        (p for p in market_data.prices if p.instrument_id == pos.instrument_id), None
    )
    if not price_entry:
        raise ValueError(
            f"Cannot value position {pos.instrument_id}: Missing price and market_value"
        )

    rate = get_fx_rate(market_data, price_entry.currency, base_ccy)
    return pos.quantity * price_entry.price * rate


def run_simulation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    model: ModelPortfolio,
    shelf: List[ShelfEntry],
    options: EngineOptions,
    request_hash: str = "sha256:dummy",
) -> RebalanceResult:

    run_id = f"rr_{uuid.uuid4().hex[:8]}"

    # 1. VALUATION (Currency Truth Model)
    total_value_base = Decimal("0.0")
    for cash in portfolio.cash_balances:
        rate = get_fx_rate(market_data, cash.currency, portfolio.base_currency)
        total_value_base += cash.amount * rate

    for pos in portfolio.positions:
        total_value_base += calculate_position_value_base(pos, market_data, portfolio.base_currency)

    # 2. UNIVERSE CONSTRUCTION & SELL_ONLY HANDLING
    eligible_targets: Dict[str, Decimal] = {}
    excluded: List[ExcludedInstrument] = []

    # We need to track what we can buy vs what we can sell for the Golden Contract
    eligible_for_buy = []
    eligible_for_sell = []
    sell_only_excess_weight = Decimal("0.0")

    for target in model.targets:
        shelf_entry = next((s for s in shelf if s.instrument_id == target.instrument_id), None)
        if not shelf_entry:
            if options.block_on_missing_prices:
                raise ValueError(f"Missing shelf entry for {target.instrument_id}")
            continue

        if shelf_entry.status in ["BANNED", "SUSPENDED"]:
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id,
                    reason_code=f"SHELF_STATUS_{shelf_entry.status}",
                )
            )
            continue

        if shelf_entry.status == "RESTRICTED" and not options.allow_restricted:
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id, reason_code="SHELF_STATUS_RESTRICTED"
                )
            )
            continue

        if shelf_entry.status == "SELL_ONLY":
            # We are not allowed to buy this. Set target to 0, save excess for redistribution.
            sell_only_excess_weight += target.weight
            eligible_targets[target.instrument_id] = Decimal("0.0")
            eligible_for_sell.append(target.instrument_id)
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id,
                    reason_code="SHELF_STATUS_SELL_ONLY_BUY_BLOCKED",
                )
            )
            continue

        # If it passed all checks, it's APPROVED or conditionally RESTRICTED
        eligible_targets[target.instrument_id] = target.weight
        eligible_for_buy.append(target.instrument_id)
        eligible_for_sell.append(target.instrument_id)

    # 3. REDISTRIBUTE SELL_ONLY EXCESS
    if sell_only_excess_weight > Decimal("0.0"):
        # We only redistribute to assets that are strictly eligible to buy
        recipients = {k: v for k, v in eligible_targets.items() if k in eligible_for_buy}
        total_rec = sum(recipients.values())
        if total_rec == Decimal("0.0"):
            raise ValueError("CONSTRAINT_INFEASIBLE: All assets are SELL_ONLY or excluded.")
        for i_id, w in recipients.items():
            eligible_targets[i_id] = w + (sell_only_excess_weight * (w / total_rec))

    # 4. CONSTRAINTS (Single Position Max)
    if options.single_position_max_weight is not None:
        max_w = options.single_position_max_weight
        excess = Decimal("0.0")
        capped = set()

        for i_id, w in eligible_targets.items():
            if w > max_w:
                excess += w - max_w
                eligible_targets[i_id] = max_w
                capped.add(i_id)

        if excess > Decimal("0.0"):
            # Only redistribute to assets that aren't capped and are eligible to buy
            recipients = {
                k: v
                for k, v in eligible_targets.items()
                if k not in capped and k in eligible_for_buy
            }
            total_rec = sum(recipients.values())
            if total_rec == Decimal("0.0"):
                raise ValueError(
                    "CONSTRAINT_INFEASIBLE: No eligible targets to absorb excess weight."
                )

            for i_id, w in recipients.items():
                new_w = w + (excess * (w / total_rec))
                if new_w > max_w:
                    raise ValueError(
                        "CONSTRAINT_INFEASIBLE: Redistribution caused secondary breach."
                    )
                eligible_targets[i_id] = new_w

    # 5. TRADE TRANSLATOR
    intents: List[OrderIntent] = []
    required_cash_by_currency: Dict[str, Decimal] = {}

    for instr_id, target_weight in eligible_targets.items():
        price_entry = next((p for p in market_data.prices if p.instrument_id == instr_id), None)
        if not price_entry:
            if options.block_on_missing_prices:
                raise ValueError(f"Missing price for {instr_id}")
            continue

        target_val_base = total_value_base * target_weight
        rate_to_base = get_fx_rate(market_data, price_entry.currency, portfolio.base_currency)
        target_val_instr = target_val_base / rate_to_base

        current_val_instr = Decimal("0.0")
        for pos in portfolio.positions:
            if pos.instrument_id == instr_id:
                if pos.market_value and pos.market_value.currency == price_entry.currency:
                    current_val_instr = pos.market_value.amount
                else:
                    current_val_instr = pos.quantity * price_entry.price

        delta_value = target_val_instr - current_val_instr

        if delta_value > Decimal("0.0"):  # BUY
            qty = int(delta_value // price_entry.price)
            notional = Decimal(qty) * price_entry.price

            shelf_entry = next((s for s in shelf if s.instrument_id == instr_id), None)
            if options.suppress_dust_trades and shelf_entry and shelf_entry.min_notional:
                if notional < shelf_entry.min_notional.amount:
                    continue

            if qty > 0:
                intents.append(
                    OrderIntent(
                        intent_id=f"oi_{len(intents) + 1}",
                        intent_type="SECURITY_TRADE",
                        side="BUY",
                        instrument_id=instr_id,
                        quantity=Decimal(qty),
                        notional=Money(amount=notional, currency=price_entry.currency),
                        rationale=IntentRationale(
                            code="DRIFT_REBALANCE", message="Align to model target"
                        ),
                    )
                )
                curr = price_entry.currency
                required_cash_by_currency[curr] = (
                    required_cash_by_currency.get(curr, Decimal("0.0")) + notional
                )

        elif delta_value < Decimal("0.0"):  # SELL
            qty = int(abs(delta_value) // price_entry.price)
            notional = Decimal(qty) * price_entry.price

            shelf_entry = next((s for s in shelf if s.instrument_id == instr_id), None)
            if options.suppress_dust_trades and shelf_entry and shelf_entry.min_notional:
                if notional < shelf_entry.min_notional.amount:
                    continue

            if qty > 0:
                intents.append(
                    OrderIntent(
                        intent_id=f"oi_{len(intents) + 1}",
                        intent_type="SECURITY_TRADE",
                        side="SELL",
                        instrument_id=instr_id,
                        quantity=Decimal(qty),
                        notional=Money(amount=notional, currency=price_entry.currency),
                        rationale=IntentRationale(
                            code="DRIFT_REBALANCE", message="Align to model target"
                        ),
                    )
                )

    # 6. FX HUB-AND-SPOKE
    fx_intent_map = {}
    for ccy, required_amt in required_cash_by_currency.items():
        if ccy == portfolio.base_currency:
            continue

        current_cash = sum(
            (c.amount for c in portfolio.cash_balances if c.currency == ccy), Decimal("0.0")
        )
        deficit = required_amt - current_cash

        if deficit > Decimal("0.0"):
            buy_amt = deficit * (Decimal("1.0") + options.fx_buffer_pct)
            rate = get_fx_rate(market_data, ccy, portfolio.base_currency)
            sell_amt = buy_amt * rate

            fx_id = f"oi_fx_{len(intents) + 1}"
            fx_intent_map[ccy] = fx_id

            intents.append(
                OrderIntent(
                    intent_id=fx_id,
                    intent_type="FX_SPOT",
                    side="BUY_BASE_SELL_QUOTE",
                    pair=f"{ccy}/{portfolio.base_currency}",
                    buy_currency=ccy,
                    buy_amount=buy_amt,
                    sell_currency=portfolio.base_currency,
                    estimated_sell_amount=sell_amt,
                    rationale=IntentRationale(
                        code="FUNDING", message="Fund foreign security purchases"
                    ),
                )
            )

    # 7. DEPENDENCY MAPPING & SORTING
    for intent in intents:
        if intent.intent_type == "SECURITY_TRADE" and intent.side == "BUY":
            req_ccy = intent.notional.currency if intent.notional else None
            if req_ccy in fx_intent_map:
                intent.dependencies.append(fx_intent_map[req_ccy])

    intents.sort(key=lambda x: 0 if x.side == "SELL" else (1 if x.intent_type == "FX_SPOT" else 2))

    # 8. AFTER-STATE SIMULATION
    after_cash = {c.currency: c.amount for c in portfolio.cash_balances}
    after_pos = {p.instrument_id: p.quantity for p in portfolio.positions}

    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            ccy = i.notional.currency
            if i.side == "BUY":
                after_cash[ccy] = after_cash.get(ccy, Decimal("0.0")) - i.notional.amount
                after_pos[i.instrument_id] = (
                    after_pos.get(i.instrument_id, Decimal("0.0")) + i.quantity
                )
            elif i.side == "SELL":
                after_cash[ccy] = after_cash.get(ccy, Decimal("0.0")) + i.notional.amount
                after_pos[i.instrument_id] = (
                    after_pos.get(i.instrument_id, Decimal("0.0")) - i.quantity
                )
        elif i.intent_type == "FX_SPOT":
            after_cash[i.sell_currency] = (
                after_cash.get(i.sell_currency, Decimal("0.0")) - i.estimated_sell_amount
            )
            after_cash[i.buy_currency] = (
                after_cash.get(i.buy_currency, Decimal("0.0")) + i.buy_amount
            )

    after_tot_base = Decimal("0.0")
    for ccy, amt in after_cash.items():
        after_tot_base += amt * get_fx_rate(market_data, ccy, portfolio.base_currency)

    for i_id, qty in after_pos.items():
        if qty > Decimal("0.0"):
            p_ent = next((p for p in market_data.prices if p.instrument_id == i_id), None)
            if p_ent:
                rate = get_fx_rate(market_data, p_ent.currency, portfolio.base_currency)
                after_tot_base += qty * p_ent.price * rate

    after_state = SimulatedState(
        total_value=Money(amount=after_tot_base, currency=portfolio.base_currency),
        cash_balances=[CashBalance(currency=k, amount=v) for k, v in after_cash.items()],
    )

    # 9. RULE ENGINE (v1)
    rule_results = []
    final_status = "READY"

    cash_val_base = sum(
        v * get_fx_rate(market_data, k, portfolio.base_currency) for k, v in after_cash.items()
    )
    cash_weight = cash_val_base / after_tot_base if after_tot_base else Decimal("0.0")

    if cash_weight > Decimal("0.05"):
        rule_results.append(
            RuleResult(
                rule_id="CASH_BAND",
                severity="SOFT",
                status="FAIL",
                measured=cash_weight,
                threshold={"max": Decimal("0.05")},
                reason_code="THRESHOLD_BREACH",
                remediation_hint="Manual review required: Excess cash drag.",
            )
        )
        final_status = "PENDING_REVIEW"
    else:
        rule_results.append(
            RuleResult(
                rule_id="CASH_BAND",
                severity="SOFT",
                status="PASS",
                measured=cash_weight,
                threshold={"max": Decimal("0.05")},
                reason_code="OK",
            )
        )

    # 10. BUILD THE GOLDEN CONTRACT
    before_state = SimulatedState(
        total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
        cash_balances=portfolio.cash_balances,
    )

    universe_data = UniverseData(
        universe_id=f"uni_{run_id}",
        eligible_for_buy=eligible_for_buy,
        eligible_for_sell=eligible_for_sell,
        excluded=excluded,
        coverage=UniverseCoverage(
            price_coverage_pct=Decimal("1.0"), fx_coverage_pct=Decimal("1.0")
        ),
    )

    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_placeholder",
        status=final_status,
        before=before_state,
        universe=universe_data,
        target=TargetData(target_id=f"tgt_{run_id}", strategy={}, targets=[]),
        intents=intents,
        after_simulated=after_state,
        rule_results=rule_results,
        explanation={"summary": f"Completed with status {final_status}."},
        diagnostics=DiagnosticsData(
            data_quality={"price_missing": [], "price_stale": [], "fx_missing": []}
        ),
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
