"""
FILE: src/core/engine.py
"""

import uuid
from copy import deepcopy
from decimal import Decimal

from src.core.compliance import RuleEngine
from src.core.models import (
    CashBalance,
    CashLadderBreach,
    CashLadderPoint,
    DiagnosticsData,
    DroppedIntent,
    EngineOptions,
    ExcludedInstrument,
    FxSpotIntent,
    GroupConstraintEvent,
    IntentRationale,
    LineageData,
    Money,
    Position,
    RebalanceResult,
    Reconciliation,
    RuleResult,
    SecurityTradeIntent,
    SuppressedIntent,
    TargetData,
    TargetMethod,
    TaxBudgetConstraintEvent,
    TaxImpact,
    UniverseCoverage,
    UniverseData,
    ValuationMode,
)
from src.core.target_generation import build_target_trace, generate_targets_solver
from src.core.valuation import build_simulated_state, get_fx_rate


def _make_empty_data_quality_log():
    return {"price_missing": [], "fx_missing": [], "shelf_missing": []}


def _make_diagnostics_data():
    return DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        group_constraint_events=[],
        data_quality=_make_empty_data_quality_log(),
    )


def _calculate_turnover_score(intent, portfolio_value_base):
    if portfolio_value_base <= Decimal("0"):
        return Decimal("0")
    return abs(intent.notional_base.amount) / portfolio_value_base


def _apply_turnover_limit(
    intents,
    options,
    portfolio_value_base,
    base_currency,
    diagnostics,
):
    if options.max_turnover_pct is None:
        return intents

    budget = portfolio_value_base * options.max_turnover_pct
    proposed = sum(abs(intent.notional_base.amount) for intent in intents)
    if proposed <= budget:
        return intents

    ranked = sorted(
        intents,
        key=lambda intent: (
            -_calculate_turnover_score(intent, portfolio_value_base),
            abs(intent.notional_base.amount),
            intent.instrument_id,
            intent.intent_id,
        ),
    )

    selected = []
    used = Decimal("0")
    for intent in ranked:
        notional_abs = abs(intent.notional_base.amount)
        score = _calculate_turnover_score(intent, portfolio_value_base)
        if used + notional_abs <= budget:
            selected.append(intent)
            used += notional_abs
            continue

        diagnostics.dropped_intents.append(
            DroppedIntent(
                instrument_id=intent.instrument_id,
                reason="TURNOVER_LIMIT",
                potential_notional=Money(amount=notional_abs, currency=base_currency),
                score=score,
            )
        )

    if diagnostics.dropped_intents:
        diagnostics.warnings.append("PARTIAL_REBALANCE_TURNOVER_LIMIT")

    return selected


def _make_blocked_result(
    run_id,
    portfolio,
    before,
    buy_l,
    sell_l,
    excl,
    trace,
    options,
    diagnostics,
    request_hash,
):
    """Create a consistent blocked response payload."""
    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_none",
        status="BLOCKED",
        before=before,
        universe=UniverseData(
            universe_id=f"u_{run_id}",
            eligible_for_buy=buy_l,
            eligible_for_sell=sell_l,
            excluded=excl,
            coverage=UniverseCoverage(price_coverage_pct=0, fx_coverage_pct=0),
        ),
        target=TargetData(target_id=f"t_{run_id}", strategy={}, targets=trace),
        intents=[],
        after_simulated=before,
        rule_results=RuleEngine.evaluate(before, options, diagnostics),
        diagnostics=diagnostics,
        explanation={"summary": "Blocked"},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )


def _build_universe(model, portfolio, shelf, options, dq_log, current_val):
    """Stage 2: Filter targets and handle implicit locking/sells."""
    eligible_targets, excluded = {}, []
    buy_list, sell_list = [], []
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
            sell_list.append(target.instrument_id)
            excluded.append(
                ExcludedInstrument(
                    instrument_id=target.instrument_id, reason_code="SHELF_STATUS_SELL_ONLY"
                )
            )
            continue
        eligible_targets[target.instrument_id] = target.weight
        buy_list.append(target.instrument_id)
        sell_list.append(target.instrument_id)

    for pos in portfolio.positions:
        if pos.quantity != 0 and pos.instrument_id not in eligible_targets:
            shelf_ent = next((s for s in shelf if s.instrument_id == pos.instrument_id), None)
            curr = next(
                (p for p in current_val.positions if p.instrument_id == pos.instrument_id), None
            )
            if not shelf_ent:
                if curr:
                    eligible_targets[pos.instrument_id] = curr.weight
                    excluded.append(
                        ExcludedInstrument(
                            instrument_id=pos.instrument_id,
                            reason_code="LOCKED_DUE_TO_MISSING_SHELF",
                        )
                    )
            elif shelf_ent.status in ["SUSPENDED", "BANNED", "RESTRICTED"]:
                if curr:
                    eligible_targets[pos.instrument_id] = curr.weight
                    excluded.append(
                        ExcludedInstrument(
                            instrument_id=pos.instrument_id,
                            reason_code=f"LOCKED_DUE_TO_{shelf_ent.status}",
                        )
                    )
            else:
                eligible_targets[pos.instrument_id] = Decimal("0.0")
                sell_list.append(pos.instrument_id)

    return eligible_targets, excluded, buy_list, sell_list, sell_only_excess


def _apply_group_constraints(eligible_targets, buy_list, shelf, options, diagnostics):
    """
    RFC-0008: Apply multi-dimensional group constraints.
    Caps overweight groups and redistributes excess to eligible buyable instruments.
    """
    if not options.group_constraints:
        return "READY"

    # Sort keys for deterministic application order
    sorted_keys = sorted(options.group_constraints.keys())

    for constraint_key in sorted_keys:
        constraint = options.group_constraints[constraint_key]

        try:
            attr_key, attr_val = constraint_key.split(":", 1)
        except ValueError:
            diagnostics.warnings.append(f"INVALID_CONSTRAINT_KEY_{constraint_key}")
            continue

        if not any(attr_key in s.attributes for s in shelf):
            diagnostics.warnings.append(f"UNKNOWN_CONSTRAINT_ATTRIBUTE_{attr_key}")
            continue

        # Identify group members
        group_members = []
        for i_id in eligible_targets:
            s_ent = next((s for s in shelf if s.instrument_id == i_id), None)
            if s_ent and s_ent.attributes.get(attr_key) == attr_val:
                group_members.append(i_id)

        if not group_members:
            continue

        current_w = sum(eligible_targets[i] for i in group_members)

        # Check tolerance (0.0001) to avoid micro-adjustments
        if current_w <= constraint.max_weight + Decimal("0.0001"):
            continue

        # Breach Detected
        scale = constraint.max_weight / current_w
        excess = current_w - constraint.max_weight

        # Scale down group members
        for i_id in group_members:
            eligible_targets[i_id] *= scale

        # Identify redistribution candidates (Must be in buy_list and NOT in the constrained group)
        candidates = [i for i in eligible_targets if i in buy_list and i not in group_members]
        total_cand_w = sum(eligible_targets[c] for c in candidates)

        if total_cand_w > Decimal("0"):
            # Redistribute proportionally
            recipients = {}
            for c in candidates:
                share = excess * (eligible_targets[c] / total_cand_w)
                eligible_targets[c] += share
                recipients[c] = share

            diagnostics.warnings.append(f"CAPPED_BY_GROUP_LIMIT_{constraint_key}")
            diagnostics.group_constraint_events.append(
                GroupConstraintEvent(
                    constraint_key=constraint_key,
                    group_weight_before=current_w,
                    max_weight=constraint.max_weight,
                    released_weight=excess,
                    recipients=recipients,
                    status="CAPPED",
                )
            )
        else:
            # Trap: Cannot redistribute
            diagnostics.warnings.append(f"CAPPED_BY_GROUP_LIMIT_{constraint_key}")
            diagnostics.warnings.append("NO_ELIGIBLE_REDISTRIBUTION_DESTINATION")
            diagnostics.group_constraint_events.append(
                GroupConstraintEvent(
                    constraint_key=constraint_key,
                    group_weight_before=current_w,
                    max_weight=constraint.max_weight,
                    released_weight=excess,
                    recipients={},
                    status="BLOCKED",
                )
            )
            return "BLOCKED"

    return "READY"


def _generate_targets(
    model,
    eligible_targets,
    buy_list,
    sell_only_excess,
    shelf=None,
    options=None,
    total_val=Decimal("0"),
    base_ccy="USD",
    diagnostics=None,
):
    """Stage 3: Normalization and Constraints."""
    if shelf is None:
        shelf = []
    if options is None:
        options = EngineOptions()
    if diagnostics is None:
        diagnostics = _make_diagnostics_data()

    if options.target_method == TargetMethod.SOLVER:
        return generate_targets_solver(
            model=model,
            eligible_targets=eligible_targets,
            buy_list=buy_list,
            sell_only_excess=sell_only_excess,
            shelf=shelf,
            options=options,
            total_val=total_val,
            base_ccy=base_ccy,
            diagnostics=diagnostics,
        )

    return _generate_targets_heuristic(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=options,
        total_val=total_val,
        base_ccy=base_ccy,
        diagnostics=diagnostics,
    )


def _to_weight_map(trace):
    return {t.instrument_id: t.final_weight for t in trace}


def _compare_target_generation_methods(
    *,
    model,
    eligible_targets,
    buy_list,
    sell_only_excess,
    shelf,
    options,
    total_val,
    base_ccy,
    primary_trace,
    primary_status,
):
    primary_method = options.target_method
    alternate_method = (
        TargetMethod.SOLVER if primary_method == TargetMethod.HEURISTIC else TargetMethod.HEURISTIC
    )

    alt_options = options.model_copy(update={"target_method": alternate_method})
    alt_diag = _make_diagnostics_data()
    alt_trace, alt_status = _generate_targets(
        model=model,
        eligible_targets=deepcopy(eligible_targets),
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=alt_options,
        total_val=total_val,
        base_ccy=base_ccy,
        diagnostics=alt_diag,
    )

    primary_weights = _to_weight_map(primary_trace)
    alternate_weights = _to_weight_map(alt_trace)
    tolerance = options.compare_target_methods_tolerance
    differing_instruments = []
    for i_id in sorted(set(primary_weights.keys()) | set(alternate_weights.keys())):
        p = primary_weights.get(i_id, Decimal("0"))
        a = alternate_weights.get(i_id, Decimal("0"))
        if abs(p - a) > tolerance:
            differing_instruments.append(i_id)

    return {
        "primary_method": primary_method.value,
        "primary_status": primary_status,
        "alternate_method": alternate_method.value,
        "alternate_status": alt_status,
        "tolerance": str(tolerance),
        "differing_instruments": differing_instruments,
        "alternate_warnings": sorted(set(alt_diag.warnings)),
    }


def _generate_targets_heuristic(
    model,
    eligible_targets,
    buy_list,
    sell_only_excess,
    shelf,
    options,
    total_val,
    base_ccy,
    diagnostics,
):
    """Legacy Stage 3 heuristic implementation."""
    status = "READY"

    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in buy_list}
        total_rec = sum(recs.values())
        if total_rec > Decimal("0.0"):
            for i_id, w in recs.items():
                eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))
        else:
            status = "PENDING_REVIEW"

    group_status = _apply_group_constraints(eligible_targets, buy_list, shelf, options, diagnostics)
    if group_status == "BLOCKED":
        return [], "BLOCKED"

    total_w = sum(eligible_targets.values())
    if total_w > Decimal("1.0001"):
        tradeable_keys = [k for k in eligible_targets if k in buy_list]
        locked_w = sum(v for k, v in eligible_targets.items() if k not in buy_list)
        available_space = max(Decimal("0.0"), Decimal("1.0") - locked_w)
        if locked_w > Decimal("1.0"):
            status = "PENDING_REVIEW"
        tradeable_w = sum(eligible_targets[k] for k in tradeable_keys)
        if tradeable_w > available_space:
            if tradeable_w > Decimal("0.0"):
                scale = available_space / tradeable_w
                for k in tradeable_keys:
                    eligible_targets[k] *= scale
            status = "PENDING_REVIEW"

    if options.single_position_max_weight is not None:
        max_w = options.single_position_max_weight
        excess = sum(max(Decimal("0.0"), w - max_w) for w in eligible_targets.values())
        for i_id in eligible_targets:
            eligible_targets[i_id] = min(eligible_targets[i_id], max_w)
        if excess > Decimal("0.0"):
            cands = {k: v for k, v in eligible_targets.items() if k in buy_list and v < max_w}
            total_cand = sum(cands.values())
            if total_cand > Decimal("0.0"):
                rem = excess
                for i_id, w in cands.items():
                    share = min(rem * (w / total_cand), max_w - w)
                    eligible_targets[i_id] += share
                    rem -= share
                if rem > Decimal("0.001"):
                    status = "PENDING_REVIEW"
            else:
                status = "PENDING_REVIEW"

    if options.min_cash_buffer_pct > Decimal("0.0"):
        tw = sum(v for k, v in eligible_targets.items() if k in buy_list)
        lw = sum(v for k, v in eligible_targets.items() if k not in buy_list)
        allowed = max(Decimal("0.0"), Decimal("1.0") - options.min_cash_buffer_pct - lw)
        if tw > allowed:
            if tw > Decimal("0.0"):
                scale = allowed / tw
                for k in eligible_targets:
                    if k in buy_list:
                        eligible_targets[k] *= scale
            status = "PENDING_REVIEW"

    return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status


def _generate_intents(
    portfolio, market_data, targets, shelf, options, total_val, dq_log, diagnostics, suppressed
):
    intents = []
    total_realized_gain_base = Decimal("0")
    total_realized_loss_base = Decimal("0")
    tax_budget_used_base = Decimal("0")
    tax_budget_limit_base = options.max_realized_capital_gains

    def lot_cost_in_instrument_ccy(unit_cost, instrument_ccy):
        if unit_cost.currency == instrument_ccy:
            return unit_cost.amount
        fx = get_fx_rate(market_data, unit_cost.currency, instrument_ccy)
        if fx is None:
            dq_log["fx_missing"].append(f"{unit_cost.currency}/{instrument_ccy}")
            return None
        return unit_cost.amount * fx

    def hifo_sorted_lots(position, instrument_ccy):
        if not position or not position.lots:
            return []
        lots_with_cost = []
        for lot in position.lots:
            cost = lot_cost_in_instrument_ccy(lot.unit_cost, instrument_ccy)
            if cost is None:
                return []
            lots_with_cost.append((lot, cost))
        return sorted(
            lots_with_cost,
            key=lambda item: (item[1], item[0].purchase_date, item[0].lot_id),
            reverse=True,
        )

    def apply_tax_budget_sell_limit(position, requested_qty, sell_price, price_ccy, base_rate):
        nonlocal total_realized_gain_base, total_realized_loss_base, tax_budget_used_base

        if requested_qty <= Decimal("0"):
            return requested_qty
        if not options.enable_tax_awareness:
            return requested_qty

        sorted_lots = hifo_sorted_lots(position, price_ccy)
        if not sorted_lots:
            return requested_qty

        remaining = requested_qty
        allowed_qty = Decimal("0")
        for lot, lot_unit_cost in sorted_lots:
            if remaining <= Decimal("0"):
                break
            if lot.quantity <= Decimal("0"):
                continue

            lot_sell_qty = min(remaining, lot.quantity)
            per_unit_gain_base = (sell_price - lot_unit_cost) * base_rate
            allowed_from_lot = lot_sell_qty

            if (
                tax_budget_limit_base is not None
                and per_unit_gain_base > Decimal("0")
                and tax_budget_used_base < tax_budget_limit_base
            ):
                remaining_headroom = tax_budget_limit_base - tax_budget_used_base
                max_qty_headroom = remaining_headroom / per_unit_gain_base
                allowed_from_lot = min(lot_sell_qty, max_qty_headroom)
            elif (
                tax_budget_limit_base is not None
                and per_unit_gain_base > Decimal("0")
                and tax_budget_used_base >= tax_budget_limit_base
            ):
                allowed_from_lot = Decimal("0")

            if allowed_from_lot <= Decimal("0"):
                break

            lot_realized_base = per_unit_gain_base * allowed_from_lot
            if lot_realized_base >= Decimal("0"):
                total_realized_gain_base += lot_realized_base
                tax_budget_used_base += lot_realized_base
            else:
                total_realized_loss_base += abs(lot_realized_base)

            allowed_qty += allowed_from_lot
            remaining -= allowed_from_lot

            if allowed_from_lot < lot_sell_qty:
                break

        return allowed_qty

    target_dict = {t.instrument_id: t.final_weight for t in targets}
    for i_id, target_w in target_dict.items():
        price_ent = next((p for p in market_data.prices if p.instrument_id == i_id), None)
        if not price_ent:
            dq_log["price_missing"].append(i_id)
            continue
        rate = get_fx_rate(market_data, price_ent.currency, portfolio.base_currency)
        if not rate:
            dq_log["fx_missing"].append(f"{price_ent.currency}/{portfolio.base_currency}")
            continue

        target_instr_val = (total_val * target_w) / rate
        curr = next((p for p in portfolio.positions if p.instrument_id == i_id), None)
        curr_instr_val = (
            curr.market_value.amount
            if curr and curr.market_value
            else (curr.quantity * price_ent.price if curr else Decimal("0"))
        )

        delta = target_instr_val - curr_instr_val
        side = "BUY" if delta > 0 else "SELL"
        qty = int(abs(delta) // price_ent.price)
        quantity = Decimal(qty)

        if side == "SELL" and qty > 0:
            requested_qty = Decimal(qty)
            quantity = apply_tax_budget_sell_limit(
                position=curr,
                requested_qty=requested_qty,
                sell_price=price_ent.price,
                price_ccy=price_ent.currency,
                base_rate=rate,
            )
            if options.enable_tax_awareness and quantity < requested_qty:
                constraints = [c for c in diagnostics.warnings if c == "TAX_BUDGET_LIMIT_REACHED"]
                if not constraints:
                    diagnostics.warnings.append("TAX_BUDGET_LIMIT_REACHED")
                diagnostics.tax_budget_constraint_events.append(
                    TaxBudgetConstraintEvent(
                        instrument_id=i_id,
                        requested_quantity=requested_qty,
                        allowed_quantity=quantity,
                        reason_code="TAX_BUDGET_LIMIT_REACHED",
                    )
                )

        notional = quantity * price_ent.price
        notional_base = notional * rate

        shelf_ent = next((s for s in shelf if s.instrument_id == i_id), None)

        threshold = None
        if options.min_trade_notional:
            threshold = options.min_trade_notional
        elif shelf_ent and shelf_ent.min_notional:
            threshold = shelf_ent.min_notional

        if options.suppress_dust_trades and threshold and notional < threshold.amount:
            suppressed.append(
                SuppressedIntent(
                    instrument_id=i_id,
                    reason="BELOW_MIN_NOTIONAL",
                    intended_notional=Money(amount=notional, currency=price_ent.currency),
                    threshold=threshold,
                )
            )
            continue

        if quantity > 0:
            applied_constraints = ["MIN_NOTIONAL"] if threshold else []
            if side == "SELL" and options.enable_tax_awareness:
                requested_qty = Decimal(qty)
                if quantity < requested_qty:
                    applied_constraints.append("TAX_BUDGET")
            intents.append(
                SecurityTradeIntent(
                    intent_id=f"oi_{len(intents) + 1}",
                    side=side,
                    instrument_id=i_id,
                    quantity=quantity,
                    notional=Money(amount=notional, currency=price_ent.currency),
                    notional_base=Money(amount=notional_base, currency=portfolio.base_currency),
                    rationale=IntentRationale(code="DRIFT_REBALANCE", message="Align"),
                    constraints_applied=applied_constraints,
                )
            )

    tax_impact = None
    if options.enable_tax_awareness:
        normalized_budget_used = tax_budget_used_base
        if tax_budget_limit_base is not None:
            if abs(tax_budget_limit_base - normalized_budget_used) <= Decimal("0.0000000001"):
                normalized_budget_used = tax_budget_limit_base
        budget_limit = (
            Money(amount=tax_budget_limit_base, currency=portfolio.base_currency)
            if tax_budget_limit_base is not None
            else None
        )
        budget_used = (
            Money(
                amount=min(normalized_budget_used, tax_budget_limit_base),
                currency=portfolio.base_currency,
            )
            if tax_budget_limit_base is not None
            else None
        )
        tax_impact = TaxImpact(
            total_realized_gain=Money(
                amount=total_realized_gain_base,
                currency=portfolio.base_currency,
            ),
            total_realized_loss=Money(
                amount=total_realized_loss_base,
                currency=portfolio.base_currency,
            ),
            budget_limit=budget_limit,
            budget_used=budget_used,
        )

    return intents, tax_impact


def _build_settlement_ladder(portfolio, shelf, intents, options, diagnostics):
    settlement_days_by_instrument = {entry.instrument_id: entry.settlement_days for entry in shelf}
    max_security_day = max(
        (
            settlement_days_by_instrument.get(intent.instrument_id, 2)
            for intent in intents
            if intent.intent_type == "SECURITY_TRADE"
        ),
        default=0,
    )
    horizon_days = max(
        options.settlement_horizon_days, options.fx_settlement_days, max_security_day
    )

    flows = {}

    def ensure_currency(currency):
        if currency not in flows:
            flows[currency] = [Decimal("0")] * (horizon_days + 1)

    for cash in portfolio.cash_balances:
        ensure_currency(cash.currency)
        flows[cash.currency][0] += cash.settled if cash.settled is not None else cash.amount

    for intent in sorted(intents, key=lambda item: item.intent_id):
        if intent.intent_type == "SECURITY_TRADE":
            settlement_day = settlement_days_by_instrument.get(intent.instrument_id, 2)
            ensure_currency(intent.notional.currency)
            signed_flow = (
                intent.notional.amount if intent.side == "SELL" else -intent.notional.amount
            )
            flows[intent.notional.currency][settlement_day] += signed_flow
            continue

        ensure_currency(intent.sell_currency)
        ensure_currency(intent.buy_currency)
        flows[intent.sell_currency][options.fx_settlement_days] -= intent.sell_amount_estimated
        flows[intent.buy_currency][options.fx_settlement_days] += intent.buy_amount

    overdraft_utilized = False
    for currency in sorted(flows.keys()):
        projected_balance = Decimal("0")
        allowed_floor = -options.max_overdraft_by_ccy.get(currency, Decimal("0"))
        for day in range(horizon_days + 1):
            projected_balance += flows[currency][day]
            diagnostics.cash_ladder.append(
                CashLadderPoint(
                    date_offset=day,
                    currency=currency,
                    projected_balance=projected_balance,
                )
            )
            if projected_balance < Decimal("0") and options.max_overdraft_by_ccy.get(
                currency, Decimal("0")
            ) > Decimal("0"):
                overdraft_utilized = True
            if projected_balance < allowed_floor:
                diagnostics.cash_ladder_breaches.append(
                    CashLadderBreach(
                        date_offset=day,
                        currency=currency,
                        projected_balance=projected_balance,
                        allowed_floor=allowed_floor,
                        reason_code=f"OVERDRAFT_ON_T_PLUS_{day}",
                    )
                )

    if overdraft_utilized:
        diagnostics.warnings.append("SETTLEMENT_OVERDRAFT_UTILIZED")


def _generate_fx_and_simulate(
    portfolio, market_data, shelf, intents, options, total_val_before, diagnostics
):
    """
    Applies intents, generates FX, checks Safety Guards, and computes Reconciliation.
    """
    proj = {c.currency: c.amount for c in portfolio.cash_balances}
    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            proj[i.notional.currency] = proj.get(i.notional.currency, Decimal("0")) + (
                i.notional.amount if i.side == "SELL" else -i.notional.amount
            )

    fx_map = {}
    for ccy, bal in proj.items():
        if ccy == portfolio.base_currency:
            continue
        rate = get_fx_rate(market_data, ccy, portfolio.base_currency)
        if rate is None:
            diagnostics.data_quality.setdefault("fx_missing", []).append(
                f"{ccy}/{portfolio.base_currency}"
            )
            if options.block_on_missing_fx:
                return intents, deepcopy(portfolio), [], "BLOCKED", None
            continue

        if bal < 0:
            buy_amt = abs(bal) * (Decimal("1.0") + options.fx_buffer_pct)
            sell_amt = buy_amt * rate
            fx_id = f"oi_fx_{len(intents) + 1}"
            fx_map[ccy] = fx_id
            intents.append(
                FxSpotIntent(
                    intent_id=fx_id,
                    pair=f"{ccy}/{portfolio.base_currency}",
                    buy_currency=ccy,
                    buy_amount=buy_amt,
                    sell_currency=portfolio.base_currency,
                    sell_amount_estimated=sell_amt,
                    rationale=IntentRationale(code="FUNDING", message="Fund"),
                )
            )
        elif bal > 0:
            buy_amt = bal * rate
            fx_id = f"oi_fx_{len(intents) + 1}"
            intents.append(
                FxSpotIntent(
                    intent_id=fx_id,
                    pair=f"{ccy}/{portfolio.base_currency}",
                    buy_currency=portfolio.base_currency,
                    buy_amount=buy_amt,
                    sell_currency=ccy,
                    sell_amount_estimated=bal,
                    rationale=IntentRationale(code="SWEEP", message="Sweep"),
                )
            )

    for i in intents:
        if i.intent_type == "SECURITY_TRADE" and i.side == "BUY" and i.notional.currency in fx_map:
            i.dependencies.append(fx_map[i.notional.currency])
    sell_ids = {
        i.notional.currency: i.intent_id
        for i in intents
        if i.intent_type == "SECURITY_TRADE" and i.side == "SELL"
    }
    for i in intents:
        if (
            i.intent_type == "SECURITY_TRADE"
            and i.side == "BUY"
            and i.notional.currency in sell_ids
        ):
            if sell_ids[i.notional.currency] not in i.dependencies:
                i.dependencies.append(sell_ids[i.notional.currency])

    intents.sort(
        key=lambda x: (
            0
            if (x.intent_type == "SECURITY_TRADE" and x.side == "SELL")
            else (1 if x.intent_type == "FX_SPOT" else 2)
        )
    )

    if options.enable_settlement_awareness:
        _build_settlement_ladder(portfolio, shelf, intents, options, diagnostics)
        if diagnostics.cash_ladder_breaches:
            first_breach = diagnostics.cash_ladder_breaches[0]
            diagnostics.warnings.append(first_breach.reason_code)

            blocked_state = build_simulated_state(
                deepcopy(portfolio),
                market_data,
                shelf,
                diagnostics.data_quality,
                diagnostics.warnings,
                options,
            )
            blocked_rules = [
                RuleResult(
                    rule_id="SETTLEMENT_CASH_LADDER",
                    severity="HARD",
                    status="FAIL",
                    measured=first_breach.allowed_floor - first_breach.projected_balance,
                    threshold={"min": first_breach.allowed_floor},
                    reason_code=first_breach.reason_code,
                    remediation_hint="Adjust timing, funding, or overdraft settings.",
                )
            ]
            return intents, blocked_state, blocked_rules, "BLOCKED", None

    after = deepcopy(portfolio)

    def g_pos(after_pf, i_id):
        p = next((x for x in after_pf.positions if x.instrument_id == i_id), None)
        if not p:
            p = Position(instrument_id=i_id, quantity=Decimal("0"))
            after_pf.positions.append(p)
        return p

    def g_cash(after_pf, ccy):
        c = next((x for x in after_pf.cash_balances if x.currency == ccy), None)
        if not c:
            c = CashBalance(currency=ccy, amount=Decimal("0"))
            after_pf.cash_balances.append(c)
        return c

    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            g_pos(after, i.instrument_id).quantity += i.quantity if i.side == "BUY" else -i.quantity
            g_cash(after, i.notional.currency).amount += (
                i.notional.amount if i.side == "SELL" else -i.notional.amount
            )
        elif i.intent_type == "FX_SPOT":
            g_cash(after, i.sell_currency).amount -= i.sell_amount_estimated
            g_cash(after, i.buy_currency).amount += i.buy_amount

    after_opts = options.model_copy(update={"valuation_mode": ValuationMode.CALCULATED})
    state = build_simulated_state(
        after, market_data, shelf, diagnostics.data_quality, diagnostics.warnings, after_opts
    )
    tv_after = state.total_value.amount

    rules = RuleEngine.evaluate(state, options, diagnostics)

    blocked = any(r.severity == "HARD" and r.status == "FAIL" for r in rules)

    if blocked:
        blockers = [r.rule_id for r in rules if r.severity == "HARD" and r.status == "FAIL"]
        if "NO_SHORTING" in blockers:
            diagnostics.warnings.append("SIMULATION_SAFETY_CHECK_FAILED")
        if "INSUFFICIENT_CASH" in blockers:
            diagnostics.warnings.append("SIMULATION_SAFETY_CHECK_FAILED")

        return intents, state, rules, "BLOCKED", None

    recon_diff = abs(tv_after - total_val_before)
    tolerance = Decimal("0.5") + (total_val_before * Decimal("0.0005"))

    recon = Reconciliation(
        before_total_value=Money(amount=total_val_before, currency=portfolio.base_currency),
        after_total_value=Money(amount=tv_after, currency=portfolio.base_currency),
        delta=Money(amount=tv_after - total_val_before, currency=portfolio.base_currency),
        tolerance=Money(amount=tolerance, currency=portfolio.base_currency),
        status="OK" if recon_diff <= tolerance else "MISMATCH",
    )

    if recon.status == "MISMATCH":
        rules.append(
            RuleResult(
                rule_id="RECONCILIATION",
                severity="HARD",
                status="FAIL",
                measured=recon_diff,
                threshold={"max": tolerance},
                reason_code="VALUE_MISMATCH",
                remediation_hint="Check pricing/FX or engine logic.",
            )
        )
        return intents, state, rules, "BLOCKED", recon

    final_status = "READY"
    soft_fails = [r for r in rules if r.severity == "SOFT" and r.status == "FAIL"]
    if soft_fails:
        final_status = "PENDING_REVIEW"

    return intents, state, rules, final_status, recon


def _check_blocking_dq(dq_log, options):
    if dq_log.get("shelf_missing"):
        return True
    if dq_log.get("price_missing") and options.block_on_missing_prices:
        return True
    if dq_log.get("fx_missing") and options.block_on_missing_fx:
        return True
    return False


def run_simulation(portfolio, market_data, model, shelf, options, request_hash="no_hash"):
    run_id = f"rr_{uuid.uuid4().hex[:8]}"
    diag_data = _make_diagnostics_data()

    before = build_simulated_state(
        portfolio, market_data, shelf, diag_data.data_quality, diag_data.warnings, options
    )
    tv = before.total_value.amount

    eligible, excl, buy_l, sell_l, s_exc = _build_universe(
        model, portfolio, shelf, options, diag_data.data_quality, before
    )
    eligible_before_s3 = deepcopy(eligible)

    trace, s3_stat = _generate_targets(
        model, eligible, buy_l, s_exc, shelf, options, tv, portfolio.base_currency, diag_data
    )

    target_method_comparison = None
    if options.compare_target_methods:
        target_method_comparison = _compare_target_generation_methods(
            model=model,
            eligible_targets=eligible_before_s3,
            buy_list=buy_l,
            sell_only_excess=s_exc,
            shelf=shelf,
            options=options,
            total_val=tv,
            base_ccy=portfolio.base_currency,
            primary_trace=trace,
            primary_status=s3_stat,
        )
        primary_status = target_method_comparison["primary_status"]
        alternate_status = target_method_comparison["alternate_status"]
        if primary_status != alternate_status:
            diag_data.warnings.append("TARGET_METHOD_STATUS_DIVERGENCE")
        if target_method_comparison["differing_instruments"]:
            diag_data.warnings.append("TARGET_METHOD_WEIGHT_DIVERGENCE")

    if _check_blocking_dq(diag_data.data_quality, options) or s3_stat == "BLOCKED":
        return _make_blocked_result(
            run_id=run_id,
            portfolio=portfolio,
            before=before,
            buy_l=buy_l,
            sell_l=sell_l,
            excl=excl,
            trace=trace,
            options=options,
            diagnostics=diag_data,
            request_hash=request_hash,
        )

    intents, tax_impact = _generate_intents(
        portfolio,
        market_data,
        trace,
        shelf,
        options,
        tv,
        diag_data.data_quality,
        diag_data,
        diag_data.suppressed_intents,
    )

    if _check_blocking_dq(diag_data.data_quality, options):
        # Re-wrap diagnostics if DQ fails late (though typically caught earlier)
        return _make_blocked_result(
            run_id=run_id,
            portfolio=portfolio,
            before=before,
            buy_l=buy_l,
            sell_l=sell_l,
            excl=excl,
            trace=trace,
            options=options,
            diagnostics=diag_data,
            request_hash=request_hash,
        )

    intents = _apply_turnover_limit(
        intents=intents,
        options=options,
        portfolio_value_base=tv,
        base_currency=portfolio.base_currency,
        diagnostics=diag_data,
    )

    intents, after, rules, f_stat, recon = _generate_fx_and_simulate(
        portfolio, market_data, shelf, intents, options, tv, diag_data
    )

    if s3_stat == "PENDING_REVIEW" and f_stat == "READY":
        f_stat = "PENDING_REVIEW"

    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_none",
        status=f_stat,
        before=before,
        universe=UniverseData(
            universe_id=f"u_{run_id}",
            eligible_for_buy=buy_l,
            eligible_for_sell=sell_l,
            excluded=excl,
            coverage=UniverseCoverage(price_coverage_pct=1, fx_coverage_pct=1),
        ),
        target=TargetData(target_id=f"t_{run_id}", strategy={}, targets=trace),
        intents=intents,
        after_simulated=after,
        reconciliation=recon,
        tax_impact=tax_impact,
        rule_results=rules,
        diagnostics=diag_data,
        explanation={"summary": f_stat, "target_method_comparison": target_method_comparison},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
