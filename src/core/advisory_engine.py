"""
FILE: src/core/advisory_engine.py
"""

import hashlib
import uuid
from copy import deepcopy
from decimal import Decimal

from src.core.common.simulation_shared import (
    apply_security_trade_to_portfolio,
    build_reconciliation,
    derive_status_from_rules,
    ensure_cash_balance,
)
from src.core.compliance import RuleEngine
from src.core.models import (
    CashFlowIntent,
    DiagnosticsData,
    IntentRationale,
    LineageData,
    Money,
    ProposalResult,
    ProposedCashFlow,
    ProposedTrade,
    RuleResult,
    SecurityTradeIntent,
    ValuationMode,
)
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


def _proposal_apply_cash_flow(after_pf, cash_flow):
    cash_entry = ensure_cash_balance(after_pf, cash_flow.currency)
    cash_entry.amount += cash_flow.amount


def _proposal_build_security_trade_intent(
    *,
    trade,
    market_data,
    base_currency,
    intent_id,
    dq_log,
):
    price_ent = next(
        (p for p in market_data.prices if p.instrument_id == trade.instrument_id), None
    )
    if not price_ent:
        dq_log["price_missing"].append(trade.instrument_id)
        return None, None

    fx_rate = get_fx_rate(market_data, price_ent.currency, base_currency)
    if fx_rate is None:
        dq_log["fx_missing"].append(f"{price_ent.currency}/{base_currency}")
        return None, None

    if trade.quantity is not None:
        quantity = trade.quantity
        notional_amount = quantity * price_ent.price
    else:
        if trade.notional.currency != price_ent.currency:
            return None, "PROPOSAL_INVALID_TRADE_INPUT"
        notional_amount = trade.notional.amount
        quantity = notional_amount / price_ent.price

    return (
        SecurityTradeIntent(
            intent_id=intent_id,
            side=trade.side,
            instrument_id=trade.instrument_id,
            quantity=quantity,
            notional=Money(amount=notional_amount, currency=price_ent.currency),
            notional_base=Money(amount=notional_amount * fx_rate, currency=base_currency),
            rationale=IntentRationale(code="MANUAL_PROPOSAL", message="Advisor proposed trade"),
            dependencies=[],
            constraints_applied=[],
        ),
        None,
    )


def _proposal_expected_cash_delta_base(portfolio, market_data, cash_flows, dq_log):
    total = Decimal("0")
    for cash_flow in cash_flows:
        fx_rate = get_fx_rate(market_data, cash_flow.currency, portfolio.base_currency)
        if fx_rate is None:
            dq_log["fx_missing"].append(f"{cash_flow.currency}/{portfolio.base_currency}")
            continue
        total += cash_flow.amount * fx_rate
    return total


def _proposal_run_id_from_request_hash(request_hash):
    if request_hash and request_hash != "no_hash":
        digest = hashlib.sha256(str(request_hash).encode("utf-8")).hexdigest()[:8]
        return f"pr_{digest}"
    return f"pr_{uuid.uuid4().hex[:8]}"


def run_proposal_simulation(
    *,
    portfolio,
    market_data,
    shelf,
    options,
    proposed_cash_flows,
    proposed_trades,
    request_hash="no_hash",
    idempotency_key=None,
    correlation_id="c_none",
):
    run_id = _proposal_run_id_from_request_hash(request_hash)
    diagnostics = _make_diagnostics_data()

    before = build_simulated_state(
        portfolio,
        market_data,
        shelf,
        diagnostics.data_quality,
        diagnostics.warnings,
        options,
    )
    after_portfolio = deepcopy(portfolio)

    intents = []
    hard_failures = []

    cash_flows = [ProposedCashFlow.model_validate(item) for item in proposed_cash_flows]
    trades = [ProposedTrade.model_validate(item) for item in proposed_trades]

    if options.proposal_apply_cash_flows_first:
        for idx, cash_flow in enumerate(cash_flows):
            _proposal_apply_cash_flow(after_portfolio, cash_flow)
            intents.append(
                CashFlowIntent(
                    intent_id=f"oi_cf_{idx + 1}",
                    currency=cash_flow.currency,
                    amount=cash_flow.amount,
                    description=cash_flow.description,
                )
            )
            if options.proposal_block_negative_cash:
                cash_entry = next(
                    (x for x in after_portfolio.cash_balances if x.currency == cash_flow.currency),
                    None,
                )
                if cash_entry is not None and cash_entry.amount < Decimal("0"):
                    diagnostics.warnings.append("PROPOSAL_WITHDRAWAL_NEGATIVE_CASH")
                    hard_failures.append("PROPOSAL_WITHDRAWAL_NEGATIVE_CASH")

    shelf_by_instrument = {entry.instrument_id: entry for entry in shelf}
    security_intents = []
    for idx, trade in enumerate(trades):
        shelf_entry = shelf_by_instrument.get(trade.instrument_id)
        if shelf_entry is None:
            diagnostics.data_quality["shelf_missing"].append(trade.instrument_id)
            continue

        if trade.side == "BUY" and shelf_entry.status in {"SELL_ONLY", "BANNED", "SUSPENDED"}:
            diagnostics.warnings.append("PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF")
            hard_failures.append("PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF")
            continue
        if (
            trade.side == "BUY"
            and shelf_entry.status == "RESTRICTED"
            and not options.allow_restricted
        ):
            diagnostics.warnings.append("PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF")
            hard_failures.append("PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF")
            continue

        intent, error_code = _proposal_build_security_trade_intent(
            trade=trade,
            market_data=market_data,
            base_currency=portfolio.base_currency,
            intent_id=f"oi_{idx + 1}",
            dq_log=diagnostics.data_quality,
        )
        if error_code:
            diagnostics.warnings.append(error_code)
            hard_failures.append(error_code)
        if intent is not None:
            security_intents.append(intent)

    sell_intents = sorted(
        [intent for intent in security_intents if intent.side == "SELL"],
        key=lambda intent: intent.instrument_id,
    )
    buy_intents = sorted(
        [intent for intent in security_intents if intent.side == "BUY"],
        key=lambda intent: intent.instrument_id,
    )

    ordered_security_intents = sell_intents + buy_intents
    intents.extend(ordered_security_intents)
    for trade_intent in ordered_security_intents:
        apply_security_trade_to_portfolio(after_portfolio, trade_intent)

    if not options.proposal_apply_cash_flows_first:
        for idx, cash_flow in enumerate(cash_flows):
            _proposal_apply_cash_flow(after_portfolio, cash_flow)
            intents.append(
                CashFlowIntent(
                    intent_id=f"oi_cf_{idx + 1}",
                    currency=cash_flow.currency,
                    amount=cash_flow.amount,
                    description=cash_flow.description,
                )
            )

    after = build_simulated_state(
        after_portfolio,
        market_data,
        shelf,
        diagnostics.data_quality,
        diagnostics.warnings,
        options.model_copy(update={"valuation_mode": ValuationMode.CALCULATED}),
    )
    rule_results = RuleEngine.evaluate(after, options, diagnostics)

    if hard_failures:
        measured = Decimal(len(hard_failures))
        rule_results.append(
            RuleResult(
                rule_id="PROPOSAL_INPUT_GUARDS",
                severity="HARD",
                status="FAIL",
                measured=measured,
                threshold={"max": Decimal("0")},
                reason_code=hard_failures[0],
                remediation_hint="Adjust proposal cash flows or shelf-ineligible buys.",
            )
        )

    final_status = derive_status_from_rules(rule_results)

    expected_delta_base = _proposal_expected_cash_delta_base(
        portfolio=portfolio,
        market_data=market_data,
        cash_flows=cash_flows,
        dq_log=diagnostics.data_quality,
    )
    expected_after_total = before.total_value.amount + expected_delta_base
    reconciliation, recon_diff, tolerance = build_reconciliation(
        before_total=before.total_value.amount,
        after_total=after.total_value.amount,
        expected_after_total=expected_after_total,
        base_currency=portfolio.base_currency,
        use_absolute_scale=True,
    )

    if reconciliation.status == "MISMATCH":
        final_status = "BLOCKED"
        rule_results.append(
            RuleResult(
                rule_id="RECONCILIATION",
                severity="HARD",
                status="FAIL",
                measured=recon_diff,
                threshold={"max": tolerance},
                reason_code="VALUE_MISMATCH",
                remediation_hint="Check pricing/FX or proposal inputs.",
            )
        )

    return ProposalResult(
        proposal_run_id=run_id,
        correlation_id=correlation_id,
        status=final_status,
        before=before,
        intents=intents,
        after_simulated=after,
        reconciliation=reconciliation,
        rule_results=rule_results,
        diagnostics=diagnostics,
        explanation={"summary": final_status},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.snapshot_id or portfolio.portfolio_id,
            market_data_snapshot_id=market_data.snapshot_id or "md",
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            engine_version="0.1.0",
        ),
    )
