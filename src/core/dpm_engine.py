"""
FILE: src/core/dpm_engine.py
"""

import uuid
from copy import deepcopy
from decimal import Decimal

from src.core.common.diagnostics import make_diagnostics_data
from src.core.compliance import RuleEngine
from src.core.dpm.execution import (
    build_settlement_ladder as build_settlement_ladder_impl,
)
from src.core.dpm.execution import (
    check_blocking_dq as check_blocking_dq_impl,
)
from src.core.dpm.execution import (
    generate_fx_and_simulate as generate_fx_and_simulate_impl,
)
from src.core.dpm.targets import (
    apply_group_constraints as apply_group_constraints_impl,
)
from src.core.dpm.targets import (
    compare_target_generation_methods as compare_target_generation_methods_impl,
)
from src.core.dpm.targets import (
    generate_targets as generate_targets_impl,
)
from src.core.dpm.targets import (
    generate_targets_heuristic as generate_targets_heuristic_impl,
)
from src.core.dpm.turnover import (
    apply_turnover_limit as apply_turnover_limit_impl,
)
from src.core.dpm.turnover import (
    calculate_turnover_score as calculate_turnover_score_impl,
)
from src.core.dpm.universe import build_universe as build_universe_impl
from src.core.models import (
    IntentRationale,
    LineageData,
    Money,
    RebalanceResult,
    SecurityTradeIntent,
    SuppressedIntent,
    TargetData,
    TaxBudgetConstraintEvent,
    TaxImpact,
    UniverseCoverage,
    UniverseData,
)
from src.core.valuation import build_simulated_state, get_fx_rate


def _calculate_turnover_score(intent, portfolio_value_base):
    return calculate_turnover_score_impl(intent, portfolio_value_base)


def _apply_turnover_limit(
    intents,
    options,
    portfolio_value_base,
    base_currency,
    diagnostics,
):
    return apply_turnover_limit_impl(
        intents=intents,
        options=options,
        portfolio_value_base=portfolio_value_base,
        base_currency=base_currency,
        diagnostics=diagnostics,
    )


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
    return build_universe_impl(model, portfolio, shelf, options, dq_log, current_val)


def _apply_group_constraints(eligible_targets, buy_list, shelf, options, diagnostics):
    return apply_group_constraints_impl(eligible_targets, buy_list, shelf, options, diagnostics)


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
    return generate_targets_impl(
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
    return compare_target_generation_methods_impl(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=options,
        total_val=total_val,
        base_ccy=base_ccy,
        primary_trace=primary_trace,
        primary_status=primary_status,
    )


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
    return generate_targets_heuristic_impl(
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
    return build_settlement_ladder_impl(portfolio, shelf, intents, options, diagnostics)


def _generate_fx_and_simulate(
    portfolio, market_data, shelf, intents, options, total_val_before, diagnostics
):
    return generate_fx_and_simulate_impl(
        portfolio, market_data, shelf, intents, options, total_val_before, diagnostics
    )


def _check_blocking_dq(dq_log, options):
    return check_blocking_dq_impl(dq_log, options)


def run_simulation(portfolio, market_data, model, shelf, options, request_hash="no_hash"):
    run_id = f"rr_{uuid.uuid4().hex[:8]}"
    diag_data = make_diagnostics_data()

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
