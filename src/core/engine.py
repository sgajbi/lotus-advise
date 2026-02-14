"""
FILE: src/core/engine.py
"""

import uuid
from copy import deepcopy
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
    Position,
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


def _evaluate_portfolio_state(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    diagnostics_warnings: List[str],
) -> Tuple[Decimal, SimulatedState]:
    """
    Reusable logic to compute total value, positions, and allocations for ANY portfolio state
    (Before or After).
    """
    total_value_base = Decimal("0.0")
    positions_summary: List[PositionSummary] = []
    allocation_by_asset: Dict[str, Decimal] = {}
    allocation_by_instr: Dict[str, Decimal] = {}

    # --- 1. Cash Valuation ---
    for cash in portfolio.cash_balances:
        rate = get_fx_rate(market_data, cash.currency, portfolio.base_currency)
        if rate is None:
            if cash.amount != 0:
                dq_log["fx_missing"].append(f"{cash.currency}/{portfolio.base_currency}")
        else:
            val_base = cash.amount * rate
            total_value_base += val_base
            # Cash Bucket
            allocation_by_asset["CASH"] = allocation_by_asset.get("CASH", Decimal("0")) + val_base

    # --- 2. Position Valuation ---
    for pos in portfolio.positions:
        if pos.quantity == 0:
            continue

        # Find Price
        price_ent = next(
            (p for p in market_data.prices if p.instrument_id == pos.instrument_id), None
        )
        if not price_ent:
            dq_log["price_missing"].append(pos.instrument_id)
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
            if pos.market_value.currency == portfolio.base_currency:
                snapshot_val_base = pos.market_value.amount
                if computed_val_base != 0:
                    diff_pct = abs(snapshot_val_base - computed_val_base) / computed_val_base
                    if diff_pct > Decimal("0.005"):
                        diagnostics_warnings.append(
                            f"POSITION_VALUE_MISMATCH: {pos.instrument_id} "
                            f"Snapshot={snapshot_val_base} Computed={computed_val_base}"
                        )
                final_val_base = snapshot_val_base

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

    sim_state = SimulatedState(
        total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
        cash_balances=portfolio.cash_balances,
        positions=positions_summary,
        allocation_by_asset_class=alloc_asset_objs,
        allocation_by_instrument=alloc_instr_objs,
        allocation=alloc_asset_objs,  # Legacy
    )

    return total_value_base, sim_state


def _calculate_valuation(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    diagnostics_warnings: List[str],
) -> Tuple[Decimal, SimulatedState]:
    """Wrapper for _evaluate_portfolio_state for the 'Before' state."""
    return _evaluate_portfolio_state(portfolio, market_data, shelf, dq_log, diagnostics_warnings)


def _build_universe(
    model: ModelPortfolio,
    portfolio: PortfolioSnapshot,
    shelf: List[ShelfEntry],
    options: EngineOptions,
    dq_log: Dict,
) -> Tuple[Dict[str, Decimal], List[ExcludedInstrument], List[str], List[str], Decimal]:
    """
    Stage 2: Determine eligible assets and targets.
    Includes both Model Targets AND Implicit Sell-to-Zero for unlisted holdings.
    """
    eligible_targets: Dict[str, Decimal] = {}
    excluded: List[ExcludedInstrument] = []
    eligible_for_buy, eligible_for_sell = [], []
    sell_only_excess = Decimal("0.0")

    # 1. Process Model Targets
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

    # 2. Process Implicit Sells (Assets held but not in Model)
    for pos in portfolio.positions:
        if pos.quantity > 0 and pos.instrument_id not in eligible_targets:
            # It's a holding not in the model. Target = 0%.
            eligible_targets[pos.instrument_id] = Decimal("0.0")
            eligible_for_sell.append(pos.instrument_id)

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

    # Sell-Only Redistribution (Simple Pro-Rata)
    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in eligible_for_buy}
        total_rec = sum(recs.values())
        if total_rec == Decimal("0.0"):
            status = "BLOCKED"  # Nowhere to put the sell proceeds? Wait, this is weight allocation.
            # If no eligible buys, excess stays unallocated (Cash).
            # Changing logic to be Best Effort:
            pass
        else:
            for i_id, w in recs.items():
                eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))

    # Single Position Max Constraint (Best Effort)
    if options.single_position_max_weight is not None:
        max_w = options.single_position_max_weight
        excess = Decimal("0.0")

        # 1. Cap all positions initially
        for i_id, w in eligible_targets.items():
            if w > max_w:
                excess += w - max_w
                eligible_targets[i_id] = max_w

        # 2. Redistribute Excess (Iteratively or Simple?)
        # Simple redistribution might breach caps again.
        # Strict logic implies we should check again.
        # Best Effort: Distribute to those BELOW cap. If everyone at cap, dump to cash.

        if excess > Decimal("0.0"):
            # Find candidates who have room
            candidates = {
                k: v for k, v in eligible_targets.items() if k in eligible_for_buy and v < max_w
            }

            total_candidate_weight = sum(candidates.values())

            if total_candidate_weight > Decimal("0.0"):
                # Distribute proportional to weight? Or equal? Proportional is standard.
                # Note: This single pass might overflow them again.
                # For MVP Institution-Grade, we do one pass. If they hit cap, we clamp and give up.

                remaining_excess = excess
                for i_id, w in candidates.items():
                    # How much room?
                    room = max_w - w
                    # Share of excess
                    share = excess * (w / total_candidate_weight)

                    to_add = min(share, room)  # Clamp to room
                    eligible_targets[i_id] += to_add
                    remaining_excess -= to_add

                # If we still have excess, it becomes Unallocated Cash.
                if remaining_excess > Decimal("0.001"):  # Tolerance
                    status = "PENDING_REVIEW"  # Soft Fail: Could not invest 100%
            else:
                # No candidates have room. Excess -> Cash.
                status = "PENDING_REVIEW"

    # Cash Buffer Scaling
    if options.min_cash_buffer_pct > Decimal("0.0"):
        total_invested_weight = sum(eligible_targets.values())
        max_allowed_weight = Decimal("1.0") - options.min_cash_buffer_pct
        if total_invested_weight > max_allowed_weight:
            scale_factor = max_allowed_weight / total_invested_weight
            for i_id in eligible_targets:
                eligible_targets[i_id] *= scale_factor

    target_trace = []
    # Trace Model Targets
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

    # Trace Implicit Sells
    for i_id in eligible_targets:
        is_in_model = any(t.instrument_id == i_id for t in model.targets)
        if not is_in_model:
            target_trace.append(
                TargetInstrument(
                    instrument_id=i_id,
                    model_weight=Decimal("0.0"),
                    final_weight=Decimal("0.0"),
                    final_value=Money(amount=Decimal("0.0"), currency=base_currency),
                    tags=["IMPLICIT_SELL_TO_ZERO"],
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
) -> List[OrderIntent]:
    """Stage 4: Convert Target Weights to Order Intents."""
    intents = []

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

    return intents


def _apply_intents(portfolio: PortfolioSnapshot, intents: List[OrderIntent]) -> PortfolioSnapshot:
    """
    Applies trades to a copy of the portfolio to generate the 'Simulated Snapshot'.
    """
    new_pf = deepcopy(portfolio)

    def get_pos(i_id):
        p = next((x for x in new_pf.positions if x.instrument_id == i_id), None)
        if not p:
            p = Position(instrument_id=i_id, quantity=Decimal("0"))
            new_pf.positions.append(p)
        return p

    def get_cash(ccy):
        c = next((x for x in new_pf.cash_balances if x.currency == ccy), None)
        if not c:
            c = CashBalance(currency=ccy, amount=Decimal("0"))
            new_pf.cash_balances.append(c)
        return c

    for intent in intents:
        if intent.intent_type == "SECURITY_TRADE":
            pos = get_pos(intent.instrument_id)
            if intent.side == "BUY":
                pos.quantity += intent.quantity
            else:
                pos.quantity -= intent.quantity

            cash_bal = get_cash(intent.notional.currency)
            if intent.side == "SELL":
                cash_bal.amount += intent.notional.amount
            else:
                cash_bal.amount -= intent.notional.amount

        elif intent.intent_type == "FX_SPOT":
            sell_bal = get_cash(intent.sell_currency)
            sell_bal.amount -= intent.estimated_sell_amount

            buy_bal = get_cash(intent.buy_currency)
            buy_bal.amount += intent.buy_amount

    return new_pf


def _generate_fx_and_simulate(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    intents: List[OrderIntent],
    options: EngineOptions,
    total_value_base: Decimal,
) -> Tuple[List[OrderIntent], SimulatedState, List[RuleResult], str]:
    """Stage 5: FX Hub-and-Spoke (Deficit & Surplus), Sorting, and After-State."""

    # 1. Calculate Projected Balances based on Security Trades
    projected_balances = {c.currency: c.amount for c in portfolio.cash_balances}

    for intent in intents:
        if intent.intent_type == "SECURITY_TRADE":
            ccy = intent.notional.currency
            current = projected_balances.get(ccy, Decimal("0.0"))
            if intent.side == "BUY":
                projected_balances[ccy] = current - intent.notional.amount
            else:
                projected_balances[ccy] = current + intent.notional.amount

    # 2. Generate FX Intents (Hub-and-Spoke)
    fx_map = {}

    for ccy, balance in projected_balances.items():
        if ccy == portfolio.base_currency:
            continue

        # Funding Deficit (BUY CCY / SELL BASE)
        if balance < 0:
            req_amount = abs(balance)
            buy_amt = req_amount * (Decimal("1.0") + options.fx_buffer_pct)
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

        # Repatriation Surplus (SELL CCY / BUY BASE)
        elif balance > 0:
            sell_amt = balance
            buy_amt = sell_amt * get_fx_rate(market_data, ccy, portfolio.base_currency)

            fx_id = f"oi_fx_{len(intents) + 1}"

            intents.append(
                OrderIntent(
                    intent_id=fx_id,
                    intent_type="FX_SPOT",
                    side="SELL_BASE_BUY_QUOTE",
                    pair=f"{ccy}/{portfolio.base_currency}",
                    buy_currency=portfolio.base_currency,
                    buy_amount=buy_amt,
                    sell_currency=ccy,
                    estimated_sell_amount=sell_amt,
                    rationale=IntentRationale(
                        code="REPATRIATION", message="Sweep excess cash to base"
                    ),
                )
            )

    # Link Dependencies (FX Funding)
    for i in intents:
        if i.intent_type == "SECURITY_TRADE" and i.side == "BUY" and i.notional.currency in fx_map:
            if fx_map[i.notional.currency] not in i.dependencies:
                i.dependencies.append(fx_map[i.notional.currency])

    # Link Dependencies (Sell-to-Fund in Same Currency)
    buys = [i for i in intents if i.intent_type == "SECURITY_TRADE" and i.side == "BUY"]
    sells = [i for i in intents if i.intent_type == "SECURITY_TRADE" and i.side == "SELL"]

    sell_map = {}
    for s in sells:
        ccy = s.notional.currency
        if ccy not in sell_map:
            sell_map[ccy] = []
        sell_map[ccy].append(s.intent_id)

    start_cash = {c.currency: c.amount for c in portfolio.cash_balances}
    for b in buys:
        ccy = b.notional.currency
        current_bal = start_cash.get(ccy, Decimal("0.0"))
        if current_bal < b.notional.amount:
            if ccy in sell_map:
                for s_id in sell_map[ccy]:
                    if s_id not in b.dependencies:
                        b.dependencies.append(s_id)

    # Sort: SELL -> FX -> BUY
    intents.sort(key=lambda x: 0 if x.side == "SELL" else (1 if x.intent_type == "FX_SPOT" else 2))

    # --- Simulation (Rich After-State) ---
    after_portfolio = _apply_intents(portfolio, intents)

    _, after_state = _evaluate_portfolio_state(
        after_portfolio, market_data, shelf, dq_log={}, diagnostics_warnings=[]
    )

    # --- Rule Engine ---
    cash_metric = next((a for a in after_state.allocation_by_asset_class if a.key == "CASH"), None)
    cash_weight = cash_metric.weight if cash_metric else Decimal("0.0")

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

    # Final Status: If targets were partial (Stage 3 returned PENDING_REVIEW) OR rules failed.
    # Note: We rely on the stage3 status passed down?
    # Current design: run_simulation passes stage3_status into this func? No.
    # We need to respect the "upstream" status.
    # Refactor: We need _generate_fx_and_simulate to accept an `initial_status`.

    # Hack for Slice 6: Calculate local status and if Rule Fail -> PENDING_REVIEW.
    final_status = "READY"
    if any(r.status == "FAIL" for r in rule_results):
        final_status = "PENDING_REVIEW"

    return intents, after_state, rule_results, final_status


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
    targets, excluded, buy_list, sell_list, excess = _build_universe(
        model, portfolio, shelf, options, dq_log
    )

    # Stage 3: Targets
    target_trace, stage3_status = _generate_targets(
        model, targets, buy_list, excess, options, total_val, portfolio.base_currency
    )

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
                data_quality=dq_log, suppressed_intents=suppressed, warnings=diagnostics_warnings
            ),
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    # Stage 4: Intents
    intents = _generate_intents(
        portfolio, market_data, targets, shelf, options, total_val, dq_log, suppressed
    )

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
                data_quality=dq_log, suppressed_intents=suppressed, warnings=diagnostics_warnings
            ),
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    # Stage 5: Simulation & Rules
    intents, after_state, rule_results, final_status = _generate_fx_and_simulate(
        portfolio, market_data, shelf, intents, options, total_val
    )

    # If Stage 3 was PENDING_REVIEW (Partial alloc), propagate it unless blocked.
    if stage3_status == "PENDING_REVIEW" and final_status == "READY":
        final_status = "PENDING_REVIEW"

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
            data_quality=dq_log, suppressed_intents=suppressed, warnings=diagnostics_warnings
        ),
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
