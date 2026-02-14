import uuid
from decimal import Decimal
from typing import Dict, List, Optional

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
    SuppressedIntent,
    TargetData,
    TargetInstrument,
    UniverseCoverage,
    UniverseData,
)


def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Optional[Decimal]:
    if from_ccy == to_ccy:
        return Decimal("1.0")
    pair_name = f"{from_ccy}/{to_ccy}"
    rate_entry = next((fx for fx in market_data.fx_rates if fx.pair == pair_name), None)
    return rate_entry.rate if rate_entry else None


def calculate_position_value_base(
    pos, market_data: MarketDataSnapshot, base_ccy: str, dq_log: Dict[str, List[str]]
) -> Optional[Decimal]:
    if pos.market_value:
        rate = get_fx_rate(market_data, pos.market_value.currency, base_ccy)
        if rate is None:
            dq_log["fx_missing"].append(f"{pos.market_value.currency}/{base_ccy}")
            return None
        return pos.market_value.amount * rate

    price_ent = next((p for p in market_data.prices if p.instrument_id == pos.instrument_id), None)
    if not price_ent:
        dq_log["price_missing"].append(pos.instrument_id)
        return None

    rate = get_fx_rate(market_data, price_ent.currency, base_ccy)
    if rate is None:
        dq_log["fx_missing"].append(f"{price_ent.currency}/{base_ccy}")
        return None

    return pos.quantity * price_ent.price * rate


def run_simulation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    model: ModelPortfolio,
    shelf: List[ShelfEntry],
    options: EngineOptions,
    request_hash: str = "sha256:dummy",
) -> RebalanceResult:
    run_id = f"rr_{uuid.uuid4().hex[:8]}"
    final_status = "READY"
    dq_log = {"price_missing": [], "fx_missing": [], "shelf_missing": []}
    suppressed = []

    # 1. VALUATION & CONTEXT
    total_value_base = Decimal("0.0")
    for cash in portfolio.cash_balances:
        rate = get_fx_rate(market_data, cash.currency, portfolio.base_currency)
        if rate is None:
            dq_log["fx_missing"].append(f"{cash.currency}/{portfolio.base_currency}")
        else:
            total_value_base += cash.amount * rate

    for pos in portfolio.positions:
        val = calculate_position_value_base(pos, market_data, portfolio.base_currency, dq_log)
        if val is not None:
            total_value_base += val

    before_state = SimulatedState(
        total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
        cash_balances=portfolio.cash_balances,
    )

    # 2. UNIVERSE CONSTRUCTION
    eligible_targets: Dict[str, Decimal] = {}
    excluded: List[ExcludedInstrument] = []
    eligible_for_buy, eligible_for_sell = [], []
    sell_only_excess = Decimal("0.0")

    for target in model.targets:
        shelf_ent = next((s for s in shelf if s.instrument_id == target.instrument_id), None)
        if not shelf_ent:
            dq_log["shelf_missing"].append(target.instrument_id)
            continue

        if shelf_ent.status in ["BANNED", "SUSPENDED"]:
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id,
                    reason_code=f"SHELF_STATUS_{shelf_ent.status}",
                )
            )
            continue

        if shelf_ent.status == "RESTRICTED" and not options.allow_restricted:
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id, reason_code="SHELF_STATUS_RESTRICTED"
                )
            )
            continue

        if shelf_ent.status == "SELL_ONLY":
            sell_only_excess += target.weight
            eligible_targets[target.instrument_id] = Decimal("0.0")
            eligible_for_sell.append(target.instrument_id)
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id,
                    reason_code="SHELF_STATUS_SELL_ONLY_BUY_BLOCKED",
                )
            )
            continue

        eligible_targets[target.instrument_id] = target.weight
        eligible_for_buy.append(target.instrument_id)
        eligible_for_sell.append(target.instrument_id)

    # 3. TARGET GENERATION & WHY TRACE
    target_trace = []
    if not any(dq_log.values()):
        if sell_only_excess > Decimal("0.0"):
            recs = {k: v for k, v in eligible_targets.items() if k in eligible_for_buy}
            total_rec = sum(recs.values())
            if total_rec == Decimal("0.0"):
                final_status = "BLOCKED"
            else:
                for i_id, w in recs.items():
                    eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))

        if options.single_position_max_weight is not None:
            max_w = options.single_position_max_weight
            excess, capped = Decimal("0.0"), set()
            for i_id, w in eligible_targets.items():
                if w > max_w:
                    excess += w - max_w
                    eligible_targets[i_id] = max_w
                    capped.add(i_id)
            if excess > Decimal("0.0"):
                recs = {
                    k: v
                    for k, v in eligible_targets.items()
                    if k not in capped and k in eligible_for_buy
                }
                total_recs = sum(recs.values())
                if total_recs == Decimal("0.0"):
                    final_status = "BLOCKED"
                else:
                    for i_id, w in recs.items():
                        new_w = w + (excess * (w / total_recs))
                        if new_w > max_w:
                            final_status = "BLOCKED"
                        eligible_targets[i_id] = new_w

        for t in model.targets:
            final_w = eligible_targets.get(t.instrument_id, Decimal("0.0"))
            tags = []
            if t.instrument_id in eligible_targets:
                if t.weight > final_w:
                    tags.append("CAPPED_BY_MAX_WEIGHT")
                if final_w > t.weight:
                    tags.append("REDISTRIBUTED_RECIPIENT")
            target_trace.append(
                TargetInstrument(
                    instrument_id=t.instrument_id,
                    model_weight=t.weight,
                    final_weight=final_w,
                    final_value=Money(
                        amount=total_value_base * final_w, currency=portfolio.base_currency
                    ),
                    tags=tags,
                )
            )

    if any(dq_log.values()) or final_status == "BLOCKED":
        return RebalanceResult(
            rebalance_run_id=run_id,
            correlation_id="c_placeholder",
            status="BLOCKED",
            before=before_state,
            universe=UniverseData(
                universe_id=f"uni_{run_id}",
                eligible_for_buy=eligible_for_buy,
                eligible_for_sell=eligible_for_sell,
                excluded=excluded,
                coverage=UniverseCoverage(
                    price_coverage_pct=Decimal("0.0"), fx_coverage_pct=Decimal("0.0")
                ),
            ),
            target=TargetData(target_id=f"tgt_{run_id}", strategy={}, targets=target_trace),
            intents=[],
            after_simulated=before_state,
            explanation={"summary": "Run blocked. Check diagnostics."},
            diagnostics=DiagnosticsData(data_quality=dq_log, suppressed_intents=suppressed),
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    # 4. TRADE GENERATION
    intents: List[OrderIntent] = []
    cash_reqs: Dict[str, Decimal] = {}
    for instr_id, target_weight in eligible_targets.items():
        price_ent = next((p for p in market_data.prices if p.instrument_id == instr_id), None)
        if not price_ent:
            continue

        target_val_base = total_value_base * target_weight
        rate = get_fx_rate(market_data, price_ent.currency, portfolio.base_currency)
        target_val_instr = target_val_base / rate

        cur_val_instr = Decimal("0.0")
        for pos in portfolio.positions:
            if pos.instrument_id == instr_id:
                cur_val_instr = (
                    pos.market_value.amount if pos.market_value else pos.quantity * price_ent.price
                )

        delta = target_val_instr - cur_val_instr
        side = "BUY" if delta > 0 else "SELL"
        qty = int(abs(delta) // price_ent.price)
        notional = Decimal(qty) * price_ent.price

        shelf_ent = next((s for s in shelf if s.instrument_id == instr_id), None)
        if options.suppress_dust_trades and shelf_ent and shelf_ent.min_notional:
            if notional < shelf_ent.min_notional.amount:
                suppressed.append(
                    SuppressedIntent(
                        instrument_id=instr_id,
                        reason="BELOW_MIN_NOTIONAL",
                        intended_notional=Money(amount=notional, currency=price_ent.currency),
                        threshold=shelf_ent.min_notional,
                    )
                )
                continue

        if qty > 0:
            intents.append(
                OrderIntent(
                    intent_id=f"oi_{len(intents) + 1}",
                    side=side,
                    instrument_id=instr_id,
                    quantity=Decimal(qty),
                    notional=Money(amount=notional, currency=price_ent.currency),
                    rationale=IntentRationale(
                        code="DRIFT_REBALANCE", message="Align to model target"
                    ),
                )
            )
            if side == "BUY":
                cash_reqs[price_ent.currency] = (
                    cash_reqs.get(price_ent.currency, Decimal("0.0")) + notional
                )

    # 5. FX & SIMULATION
    fx_map = {}
    for ccy, req in cash_reqs.items():
        if ccy == portfolio.base_currency:
            continue
        cur_cash = sum(
            (c.amount for c in portfolio.cash_balances if c.currency == ccy), Decimal("0.0")
        )
        deficit = req - cur_cash
        if deficit > 0:
            buy_amt = deficit * (Decimal("1.0") + options.fx_buffer_pct)
            sell_amt = buy_amt * get_fx_rate(market_data, ccy, portfolio.base_currency)
            fx_id = f"oi_fx_{len(intents) + 1}"
            fx_map[ccy] = fx_id
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
                    rationale=IntentRationale(code="FUNDING", message="Fund foreign buys"),
                )
            )

    for i in intents:
        if i.intent_type == "SECURITY_TRADE" and i.side == "BUY" and i.notional.currency in fx_map:
            i.dependencies.append(fx_map[i.notional.currency])

    # Intent Sorting: SELLs first, then FX, then BUYs
    intents.sort(key=lambda x: 0 if x.side == "SELL" else (1 if x.intent_type == "FX_SPOT" else 2))

    after_cash = {c.currency: c.amount for c in portfolio.cash_balances}
    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            ccy = i.notional.currency
            delta_val = i.notional.amount if i.side == "SELL" else -i.notional.amount
            after_cash[ccy] = after_cash.get(ccy, Decimal("0.0")) + delta_val
        elif i.intent_type == "FX_SPOT":
            after_cash[i.sell_currency] -= i.estimated_sell_amount
            # KEY FIX: Ensure target currency exists in map
            after_cash[i.buy_currency] = (
                after_cash.get(i.buy_currency, Decimal("0.0")) + i.buy_amount
            )

    # Simplified after-state valuation
    after_val_base = sum(
        v * get_fx_rate(market_data, k, portfolio.base_currency) for k, v in after_cash.items()
    )
    cash_weight = after_val_base / total_value_base if total_value_base else Decimal("0.0")

    rule_results = [
        RuleResult(
            rule_id="CASH_BAND",
            severity="SOFT",
            status="FAIL" if cash_weight > 0.05 else "PASS",
            measured=cash_weight,
            threshold={"max": Decimal("0.05")},
            reason_code="THRESHOLD_BREACH" if cash_weight > 0.05 else "OK",
        )
    ]
    if any(r.status == "FAIL" for r in rule_results):
        final_status = "PENDING_REVIEW"

    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_placeholder",
        status=final_status,
        before=before_state,
        universe=UniverseData(
            universe_id=f"uni_{run_id}",
            eligible_for_buy=eligible_for_buy,
            eligible_for_sell=eligible_for_sell,
            excluded=excluded,
            coverage=UniverseCoverage(
                price_coverage_pct=Decimal("1.0"), fx_coverage_pct=Decimal("1.0")
            ),
        ),
        target=TargetData(target_id=f"tgt_{run_id}", strategy={}, targets=target_trace),
        intents=intents,
        after_simulated=SimulatedState(
            total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
            cash_balances=[CashBalance(currency=k, amount=v) for k, v in after_cash.items()],
        ),
        rule_results=rule_results,
        explanation={"summary": f"Status: {final_status}"},
        diagnostics=DiagnosticsData(data_quality=dq_log, suppressed_intents=suppressed),
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
