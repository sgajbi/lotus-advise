"""
FILE: src/core/engine.py
"""

import uuid
from copy import deepcopy
from decimal import Decimal

from src.core.compliance import RuleEngine
from src.core.models import (
    CashBalance,
    DiagnosticsData,
    ExcludedInstrument,
    FxSpotIntent,
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
    TargetInstrument,
    UniverseCoverage,
    UniverseData,
)
from src.core.valuation import build_simulated_state, get_fx_rate


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
        if pos.quantity > 0 and pos.instrument_id not in eligible_targets:
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


def _generate_targets(
    model, eligible_targets, buy_list, sell_only_excess, options, total_val, base_ccy
):
    """Stage 3: Normalization and Constraints."""
    status = "READY"

    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in buy_list}
        total_rec = sum(recs.values())
        if total_rec > Decimal("0.0"):
            for i_id, w in recs.items():
                eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))
        else:
            status = "PENDING_REVIEW"

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

    trace = []
    for t in model.targets:
        final_w = eligible_targets.get(t.instrument_id, Decimal("0.0"))
        tags = ["CAPPED_BY_MAX_WEIGHT"] if t.weight > final_w else []
        if final_w > t.weight:
            tags.append("REDISTRIBUTED_RECIPIENT")
        trace.append(
            TargetInstrument(
                instrument_id=t.instrument_id,
                model_weight=t.weight,
                final_weight=final_w,
                final_value=Money(amount=total_val * final_w, currency=base_ccy),
                tags=tags,
            )
        )

    for i_id, final_w in eligible_targets.items():
        if not any(t.instrument_id == i_id for t in model.targets):
            tag = (
                "IMPLICIT_SELL_TO_ZERO" if (i_id in buy_list or final_w == 0) else "LOCKED_POSITION"
            )
            trace.append(
                TargetInstrument(
                    instrument_id=i_id,
                    model_weight=Decimal("0.0"),
                    final_weight=final_w,
                    final_value=Money(amount=total_val * final_w, currency=base_ccy),
                    tags=[tag],
                )
            )

    return trace, status


def _generate_intents(
    portfolio, market_data, targets, shelf, options, total_val, dq_log, suppressed
):
    intents = []
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
        notional = Decimal(qty) * price_ent.price
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

        if qty > 0:
            intents.append(
                SecurityTradeIntent(
                    intent_id=f"oi_{len(intents) + 1}",
                    side=side,
                    instrument_id=i_id,
                    quantity=Decimal(qty),
                    notional=Money(amount=notional, currency=price_ent.currency),
                    notional_base=Money(amount=notional_base, currency=portfolio.base_currency),
                    rationale=IntentRationale(code="DRIFT_REBALANCE", message="Align"),
                    constraints_applied=["MIN_NOTIONAL"] if threshold else [],
                )
            )
    return intents


def _generate_fx_and_simulate(
    portfolio, market_data, shelf, intents, options, total_val_before, diagnostics
):
    """
    Applies intents, generates FX, checks Safety Guards, and computes Reconciliation.
    """
    # 1. Calculate projected cash by currency
    proj = {c.currency: c.amount for c in portfolio.cash_balances}
    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            proj[i.notional.currency] = proj.get(i.notional.currency, Decimal("0")) + (
                i.notional.amount if i.side == "SELL" else -i.notional.amount
            )

    # 2. Generate FX Intents
    fx_map = {}
    for ccy, bal in proj.items():
        if ccy == portfolio.base_currency:
            continue
        rate = get_fx_rate(market_data, ccy, portfolio.base_currency)
        if rate is None:
            if options.block_on_missing_fx:
                diagnostics.data_quality.setdefault("fx_missing", []).append(
                    f"{ccy}/{portfolio.base_currency}"
                )
                return intents, deepcopy(portfolio), [], "BLOCKED", None
            else:
                diagnostics.data_quality.setdefault("fx_missing", []).append(
                    f"{ccy}/{portfolio.base_currency}"
                )
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

    # 3. Link Dependencies
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

    # 4. Sort
    intents.sort(
        key=lambda x: (
            0
            if (x.intent_type == "SECURITY_TRADE" and x.side == "SELL")
            else (1 if x.intent_type == "FX_SPOT" else 2)
        )
    )

    # 5. Simulate
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

    # 6. Build State
    # RFC-0007A: Update to pass options for correct valuation mode in After State
    state = build_simulated_state(
        after, market_data, shelf, diagnostics.data_quality, diagnostics.warnings, options
    )
    tv_after = state.total_value.amount

    # 7. Evaluate Rules
    rules = RuleEngine.evaluate(state, options, diagnostics)

    # 8. Check for Hard Fails
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
    if any(r.severity == "SOFT" and r.status == "FAIL" for r in rules):
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
    dq, warns, suppressed = {"price_missing": [], "fx_missing": [], "shelf_missing": []}, [], []

    # RFC-0007A: Update to pass options for correct valuation mode in Before State
    before = build_simulated_state(portfolio, market_data, shelf, dq, warns, options)
    tv = before.total_value.amount

    eligible, excl, buy_l, sell_l, s_exc = _build_universe(
        model, portfolio, shelf, options, dq, before
    )

    trace, s3_stat = _generate_targets(
        model, eligible, buy_l, s_exc, options, tv, portfolio.base_currency
    )

    diag_data = DiagnosticsData(data_quality=dq, suppressed_intents=suppressed, warnings=warns)

    if _check_blocking_dq(dq, options) or s3_stat == "BLOCKED":
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
            rule_results=RuleEngine.evaluate(before, options, diag_data),
            diagnostics=diag_data,
            explanation={"summary": "Blocked"},
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    intents = _generate_intents(portfolio, market_data, trace, shelf, options, tv, dq, suppressed)

    if _check_blocking_dq(dq, options):
        diag_data = DiagnosticsData(data_quality=dq, suppressed_intents=suppressed, warnings=warns)
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
            rule_results=RuleEngine.evaluate(before, options, diag_data),
            diagnostics=diag_data,
            explanation={"summary": "Blocked"},
            lineage=LineageData(
                portfolio_snapshot_id=portfolio.portfolio_id,
                market_data_snapshot_id="md",
                request_hash=request_hash,
            ),
        )

    diag_data = DiagnosticsData(data_quality=dq, suppressed_intents=suppressed, warnings=warns)

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
        rule_results=rules,
        diagnostics=diag_data,
        explanation={"summary": f_stat},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
