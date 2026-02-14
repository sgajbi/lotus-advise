"""
FILE: src/core/engine.py
"""

import uuid
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.core.models import (
    AllocationMetric,
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
    PositionSummary,
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


def _calculate_valuation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    diagnostics_warnings: List[str],
) -> Tuple[Decimal, SimulatedState]:
    """
    Stage 1: Institution-Grade Valuation.
    Computes total value in base currency, position summaries, and allocations.
    """
    total_value_base = Decimal("0.0")
    positions_summary: List[PositionSummary] = []
    allocation_by_asset: Dict[str, Decimal] = {}
    allocation_by_instr: Dict[str, Decimal] = {}

    # --- 1. Cash Valuation ---
    for cash in portfolio.cash_balances:
        rate = get_fx_rate(market_data, cash.currency, portfolio.base_currency)
        if rate is None:
            dq_log["fx_missing"].append(f"{cash.currency}/{portfolio.base_currency}")
        else:
            val_base = cash.amount * rate
            total_value_base += val_base
            # Cash Bucket
            allocation_by_asset["CASH"] = allocation_by_asset.get("CASH", Decimal("0")) + val_base

    # --- 2. Position Valuation ---
    for pos in portfolio.positions:
        # Find Price
        price_ent = next(
            (p for p in market_data.prices if p.instrument_id == pos.instrument_id), None
        )
        if not price_ent:
            dq_log["price_missing"].append(pos.instrument_id)
            # Cannot proceed with valuation for this pos, skip or partial?
            # MVP: Skip implies value 0, but we log DQ. Block happens later.
            continue

        # Find FX
        rate = get_fx_rate(market_data, price_ent.currency, portfolio.base_currency)
        if rate is None:
            dq_log["fx_missing"].append(f"{price_ent.currency}/{portfolio.base_currency}")
            continue

        # Computed Value
        computed_val_instr = pos.quantity * price_ent.price
        computed_val_base = computed_val_instr * rate

        # Snapshot Value Logic (Truth vs Computed)
        final_val_base = computed_val_base
        if pos.market_value:
            # If snapshot has MV in Base, use it? Or check consistency?
            # RFC says: if snapshot MV in base, use as truth.
            if pos.market_value.currency == portfolio.base_currency:
                snapshot_val_base = pos.market_value.amount
                # Mismatch Check (0.5% tolerance)
                if computed_val_base != 0:
                    diff_pct = abs(snapshot_val_base - computed_val_base) / computed_val_base
                    if diff_pct > Decimal("0.005"):
                        diagnostics_warnings.append(
                            f"POSITION_VALUE_MISMATCH: {pos.instrument_id} "
                            f"Snapshot={snapshot_val_base} Computed={computed_val_base}"
                        )
                final_val_base = snapshot_val_base
            else:
                # Snapshot is in instr currency, verify?
                # For now, rely on computed path if base MV not provided
                pass

        total_value_base += final_val_base

        # --- Metadata & Grouping ---
        shelf_ent = next((s for s in shelf if s.instrument_id == pos.instrument_id), None)
        asset_class = shelf_ent.asset_class if shelf_ent else "UNKNOWN"

        allocation_by_asset[asset_class] = (
            allocation_by_asset.get(asset_class, Decimal("0")) + final_val_base
        )
        allocation_by_instr[pos.instrument_id] = (
            allocation_by_instr.get(pos.instrument_id, Decimal("0")) + final_val_base
        )

        positions_summary.append(
            PositionSummary(
                instrument_id=pos.instrument_id,
                quantity=pos.quantity,
                instrument_currency=price_ent.currency,
                price=Money(amount=price_ent.price, currency=price_ent.currency),
                value_in_instrument_ccy=Money(
                    amount=computed_val_instr, currency=price_ent.currency
                ),
                value_in_base_ccy=Money(amount=final_val_base, currency=portfolio.base_currency),
                weight=Decimal("0"),  # Fill in pass 2
            )
        )

    # --- 3. Weight Calculation & Object Construction ---
    # Avoid div by zero
    tv_divisor = total_value_base if total_value_base != 0 else Decimal("1")

    # Update Position Weights
    for p in positions_summary:
        p.weight = p.value_in_base_ccy.amount / tv_divisor

    # Build Allocations
    alloc_asset_objs = []
    for k, v in allocation_by_asset.items():
        alloc_asset_objs.append(
            AllocationMetric(
                key=k,
                weight=v / tv_divisor,
                value=Money(amount=v, currency=portfolio.base_currency),
            )
        )

    alloc_instr_objs = []
    for k, v in allocation_by_instr.items():
        alloc_instr_objs.append(
            AllocationMetric(
                key=k,
                weight=v / tv_divisor,
                value=Money(amount=v, currency=portfolio.base_currency),
            )
        )

    before_state = SimulatedState(
        total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
        cash_balances=portfolio.cash_balances,
        positions=positions_summary,
        allocation_by_asset_class=alloc_asset_objs,
        allocation_by_instrument=alloc_instr_objs,
        allocation=alloc_asset_objs,  # Legacy
    )

    return total_value_base, before_state


def _build_universe(
    model: ModelPortfolio, shelf: List[ShelfEntry], options: EngineOptions, dq_log: Dict
) -> Tuple[Dict[str, Decimal], List[ExcludedInstrument], List[str], List[str], Decimal]:
    """Stage 2: Filter shelf and determine eligible assets."""
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

    return eligible_targets, excluded, eligible_for_buy, eligible_for_sell, sell_only_excess


def _generate_targets(
    model: ModelPortfolio,
    eligible_targets: Dict[str, Decimal],
    eligible_for_buy: List[str],
    sell_only_excess: Decimal,
    options: EngineOptions,
    total_value_base: Decimal,
    base_currency: str,
) -> Tuple[List[TargetInstrument], str]:
    """Stage 3: Apply mathematical constraints (Capping, Redistribution) and generate trace."""
    status = "READY"

    # Sell-Only Redistribution
    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in eligible_for_buy}
        total_rec = sum(recs.values())
        if total_rec == Decimal("0.0"):
            status = "BLOCKED"
        else:
            for i_id, w in recs.items():
                eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))

    # Single Position Max Constraint
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
                status = "BLOCKED"
            else:
                for i_id, w in recs.items():
                    new_w = w + (excess * (w / total_recs))
                    if new_w > max_w:
                        status = "BLOCKED"
                    eligible_targets[i_id] = new_w

    target_trace = []
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
                final_value=Money(amount=total_value_base * final_w, currency=base_currency),
                tags=tags,
            )
        )
    return target_trace, status


def _generate_intents(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    eligible_targets: Dict[str, Decimal],
    shelf: List[ShelfEntry],
    options: EngineOptions,
    total_value_base: Decimal,
    dq_log: Dict,
    suppressed: List[SuppressedIntent],
) -> Tuple[List[OrderIntent], Dict[str, Decimal]]:
    """Stage 4: Convert Target Weights to Order Intents."""
    intents = []
    cash_reqs = {}

    for instr_id, target_weight in eligible_targets.items():
        price_ent = next((p for p in market_data.prices if p.instrument_id == instr_id), None)
        if not price_ent:
            dq_log["price_missing"].append(instr_id)
            continue

        rate = get_fx_rate(market_data, price_ent.currency, portfolio.base_currency)
        if rate is None:
            dq_log["fx_missing"].append(f"{price_ent.currency}/{portfolio.base_currency}")
            continue

        target_val_base = total_value_base * target_weight
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

        # Dust Suppression
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

    return intents, cash_reqs


def _generate_fx_and_simulate(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    intents: List[OrderIntent],
    cash_reqs: Dict[str, Decimal],
    options: EngineOptions,
    total_value_base: Decimal,
) -> Tuple[List[OrderIntent], SimulatedState, List[RuleResult], str]:
    """Stage 5: FX Hub-and-Spoke, Sorting, and After-State Validation."""
    # FX Generation
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

    # Link Dependencies
    for i in intents:
        if i.intent_type == "SECURITY_TRADE" and i.side == "BUY" and i.notional.currency in fx_map:
            i.dependencies.append(fx_map[i.notional.currency])

    # Sort: SELL -> FX -> BUY
    intents.sort(key=lambda x: 0 if x.side == "SELL" else (1 if x.intent_type == "FX_SPOT" else 2))

    # Simulation
    after_cash = {c.currency: c.amount for c in portfolio.cash_balances}
    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            ccy = i.notional.currency
            delta_val = i.notional.amount if i.side == "SELL" else -i.notional.amount
            after_cash[ccy] = after_cash.get(ccy, Decimal("0.0")) + delta_val
        elif i.intent_type == "FX_SPOT":
            after_cash[i.sell_currency] -= i.estimated_sell_amount
            after_cash[i.buy_currency] = (
                after_cash.get(i.buy_currency, Decimal("0.0")) + i.buy_amount
            )

    # Rule Engine
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
    status = "PENDING_REVIEW" if any(r.status == "FAIL" for r in rule_results) else "READY"

    after_state = SimulatedState(
        total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
        cash_balances=[CashBalance(currency=k, amount=v) for k, v in after_cash.items()],
    )
    return intents, after_state, rule_results, status


def run_simulation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    model: ModelPortfolio,
    shelf: List[ShelfEntry],
    options: EngineOptions,
    request_hash: str = "sha256:dummy",
) -> RebalanceResult:
    run_id = f"rr_{uuid.uuid4().hex[:8]}"
    dq_log = {"price_missing": [], "fx_missing": [], "shelf_missing": []}
    diagnostics_warnings = []
    suppressed = []

    # Stage 1: Valuation
    total_val, before_state = _calculate_valuation(
        portfolio, market_data, shelf, dq_log, diagnostics_warnings
    )

    # Stage 2: Universe
    targets, excluded, buy_list, sell_list, excess = _build_universe(model, shelf, options, dq_log)

    # Stage 3: Targets (Logic Branching)
    target_trace, stage3_status = _generate_targets(
        model, targets, buy_list, excess, options, total_val, portfolio.base_currency
    )

    # Exit if Stage 1-3 Failed
    if any(dq_log.values()) or stage3_status == "BLOCKED":
        return RebalanceResult(
            rebalance_run_id=run_id,
            correlation_id="c_placeholder",
            status="BLOCKED",
            before=before_state,
            universe=UniverseData(
                universe_id=f"uni_{run_id}",
                eligible_for_buy=buy_list,
                eligible_for_sell=sell_list,
                excluded=excluded,
                coverage=UniverseCoverage(
                    price_coverage_pct=Decimal("0"), fx_coverage_pct=Decimal("0")
                ),
            ),
            target=TargetData(target_id=f"tgt_{run_id}", strategy={}, targets=target_trace),
            intents=[],
            after_simulated=before_state,
            explanation={"summary": "Run blocked. Check diagnostics."},
            diagnostics=DiagnosticsData(
                data_quality=dq_log,
                suppressed_intents=suppressed,
                warnings=diagnostics_warnings,
            ),
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    # Stage 4: Intents
    intents, cash_reqs = _generate_intents(
        portfolio, market_data, targets, shelf, options, total_val, dq_log, suppressed
    )

    # Exit if Stage 4 Data Quality Failed
    if any(dq_log.values()):
        return RebalanceResult(
            rebalance_run_id=run_id,
            correlation_id="c_placeholder",
            status="BLOCKED",
            before=before_state,
            universe=UniverseData(
                universe_id=f"uni_{run_id}",
                eligible_for_buy=buy_list,
                eligible_for_sell=sell_list,
                excluded=excluded,
                coverage=UniverseCoverage(
                    price_coverage_pct=Decimal("0"), fx_coverage_pct=Decimal("0")
                ),
            ),
            target=TargetData(target_id=f"tgt_{run_id}", strategy={}, targets=target_trace),
            intents=[],
            after_simulated=before_state,
            explanation={"summary": "Run blocked during trade generation."},
            diagnostics=DiagnosticsData(
                data_quality=dq_log,
                suppressed_intents=suppressed,
                warnings=diagnostics_warnings,
            ),
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    # Stage 5: Simulation & Rules
    intents, after_state, rule_results, final_status = _generate_fx_and_simulate(
        portfolio, market_data, intents, cash_reqs, options, total_val
    )

    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_placeholder",
        status=final_status,
        before=before_state,
        universe=UniverseData(
            universe_id=f"uni_{run_id}",
            eligible_for_buy=buy_list,
            eligible_for_sell=sell_list,
            excluded=excluded,
            coverage=UniverseCoverage(
                price_coverage_pct=Decimal("1"), fx_coverage_pct=Decimal("1")
            ),
        ),
        target=TargetData(target_id=f"tgt_{run_id}", strategy={}, targets=target_trace),
        intents=intents,
        after_simulated=after_state,
        rule_results=rule_results,
        explanation={"summary": f"Status: {final_status}"},
        diagnostics=DiagnosticsData(
            data_quality=dq_log,
            suppressed_intents=suppressed,
            warnings=diagnostics_warnings,
        ),
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
