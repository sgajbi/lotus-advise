from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from src.core.advisory.funding import build_auto_funding_plan
from src.core.advisory.intents import apply_proposal_cash_flow, build_proposal_security_trade_intent
from src.core.common.intent_dependencies import link_buy_intent_dependencies
from src.core.common.simulation_shared import (
    apply_security_trade_to_portfolio,
    sort_execution_intents,
)
from src.core.diagnostics_models import DiagnosticsData
from src.core.engine_options_models import EngineOptions
from src.core.order_intent_models import (
    CashFlowIntent,
    FxSpotIntent,
    ProposalOrderIntent,
    SecurityTradeIntent,
)
from src.core.portfolio_models import MarketDataSnapshot, PortfolioSnapshot, ShelfEntry
from src.core.proposal_request_models import ProposedCashFlow, ProposedTrade


@dataclass(frozen=True)
class SimulationIntentPlan:
    after_portfolio: PortfolioSnapshot
    cash_flows: list[ProposedCashFlow]
    trades: list[ProposedTrade]
    intents: list[ProposalOrderIntent]
    hard_failures: list[str]
    force_pending_review: bool


@dataclass(frozen=True)
class _ValidatedProposalInputs:
    cash_flows: list[ProposedCashFlow]
    trades: list[ProposedTrade]


@dataclass(frozen=True)
class _SecurityIntentGroups:
    sell_intents: list[SecurityTradeIntent]
    buy_intents: list[SecurityTradeIntent]


def build_simulation_intent_plan(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    proposed_cash_flows: list[ProposedCashFlow] | list[dict[str, Any]],
    proposed_trades: list[ProposedTrade] | list[dict[str, Any]],
    diagnostics: DiagnosticsData,
) -> SimulationIntentPlan:
    after_portfolio = deepcopy(portfolio)
    hard_failures: list[str] = []
    proposal_inputs = _validated_proposal_inputs(
        proposed_cash_flows=proposed_cash_flows,
        proposed_trades=proposed_trades,
    )

    cash_flow_intents = _build_cash_flow_intents(
        after_portfolio=after_portfolio,
        cash_flows=proposal_inputs.cash_flows,
        options=options,
        diagnostics=diagnostics,
        hard_failures=hard_failures,
    )
    security_groups = _build_security_intent_groups(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        trades=proposal_inputs.trades,
        options=options,
        diagnostics=diagnostics,
        hard_failures=hard_failures,
    )

    _apply_sell_intents(
        after_portfolio=after_portfolio,
        sell_intents=security_groups.sell_intents,
    )
    fx_intents, fx_by_currency, unfunded_currencies, force_pending_review = _build_funding_intents(
        after_portfolio=after_portfolio,
        market_data=market_data,
        options=options,
        buy_intents=security_groups.buy_intents,
        diagnostics=diagnostics,
        hard_failures=hard_failures,
    )

    executable_buy_intents = _apply_executable_buy_intents(
        after_portfolio=after_portfolio,
        buy_intents=security_groups.buy_intents,
        unfunded_currencies=unfunded_currencies,
        diagnostics=diagnostics,
    )

    _link_executable_buy_dependencies(
        options=options,
        sell_intents=security_groups.sell_intents,
        executable_buy_intents=executable_buy_intents,
        fx_intent_id_by_currency=fx_by_currency,
    )

    intents = _ordered_execution_intents(
        cash_flow_intents=cash_flow_intents,
        sell_intents=security_groups.sell_intents,
        fx_intents=fx_intents,
        executable_buy_intents=executable_buy_intents,
    )

    return SimulationIntentPlan(
        after_portfolio=after_portfolio,
        cash_flows=proposal_inputs.cash_flows,
        trades=proposal_inputs.trades,
        intents=intents,
        hard_failures=hard_failures,
        force_pending_review=force_pending_review,
    )


def _validated_proposal_inputs(
    *,
    proposed_cash_flows: list[ProposedCashFlow] | list[dict[str, Any]],
    proposed_trades: list[ProposedTrade] | list[dict[str, Any]],
) -> _ValidatedProposalInputs:
    return _ValidatedProposalInputs(
        cash_flows=[ProposedCashFlow.model_validate(item) for item in proposed_cash_flows],
        trades=[ProposedTrade.model_validate(item) for item in proposed_trades],
    )


def _build_security_intent_groups(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    trades: list[ProposedTrade],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    hard_failures: list[str],
) -> _SecurityIntentGroups:
    security_intents = _build_security_trade_intents(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        trades=trades,
        options=options,
        diagnostics=diagnostics,
        hard_failures=hard_failures,
    )
    return _SecurityIntentGroups(
        sell_intents=_sorted_security_intents_by_instrument(security_intents, side="SELL"),
        buy_intents=_sorted_security_intents_by_instrument(security_intents, side="BUY"),
    )


def _sorted_security_intents_by_instrument(
    intents: list[SecurityTradeIntent],
    *,
    side: str,
) -> list[SecurityTradeIntent]:
    return sorted(
        [intent for intent in intents if intent.side == side],
        key=lambda intent: intent.instrument_id,
    )


def _apply_sell_intents(
    *,
    after_portfolio: PortfolioSnapshot,
    sell_intents: list[SecurityTradeIntent],
) -> None:
    for sell_intent in sell_intents:
        apply_security_trade_to_portfolio(after_portfolio, sell_intent)


def _build_funding_intents(
    *,
    after_portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    options: EngineOptions,
    buy_intents: list[SecurityTradeIntent],
    diagnostics: DiagnosticsData,
    hard_failures: list[str],
) -> tuple[list[FxSpotIntent], dict[str, str], set[str], bool]:
    (
        fx_intents,
        fx_by_currency,
        unfunded_currencies,
        funding_failures,
        funding_pending,
    ) = build_auto_funding_plan(
        after_portfolio=after_portfolio,
        market_data=market_data,
        options=options,
        buy_intents=buy_intents,
        diagnostics=diagnostics,
    )
    hard_failures.extend(funding_failures)
    return fx_intents, fx_by_currency, unfunded_currencies, funding_pending


def _link_executable_buy_dependencies(
    *,
    options: EngineOptions,
    sell_intents: list[SecurityTradeIntent],
    executable_buy_intents: list[SecurityTradeIntent],
    fx_intent_id_by_currency: dict[str, str],
) -> None:
    include_sell_dependency = options.link_buy_to_same_currency_sell_dependency or False
    link_buy_intent_dependencies(
        sell_intents + executable_buy_intents,
        fx_intent_id_by_currency=fx_intent_id_by_currency,
        include_same_currency_sell_dependency=include_sell_dependency,
    )


def _ordered_execution_intents(
    *,
    cash_flow_intents: list[CashFlowIntent],
    sell_intents: list[SecurityTradeIntent],
    fx_intents: list[FxSpotIntent],
    executable_buy_intents: list[SecurityTradeIntent],
) -> list[ProposalOrderIntent]:
    ordered_fx_intents = sorted(fx_intents, key=lambda intent: intent.pair)
    return cast(
        list[ProposalOrderIntent],
        sort_execution_intents(
            cash_flow_intents + sell_intents + ordered_fx_intents + executable_buy_intents
        ),
    )


def _build_cash_flow_intents(
    *,
    after_portfolio: PortfolioSnapshot,
    cash_flows: list[ProposedCashFlow],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    hard_failures: list[str],
) -> list[CashFlowIntent]:
    cash_flow_intents: list[CashFlowIntent] = []
    for idx, cash_flow in enumerate(cash_flows):
        apply_proposal_cash_flow(after_portfolio, cash_flow)
        cash_flow_intents.append(
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
    return cash_flow_intents


def _build_security_trade_intents(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    trades: list[ProposedTrade],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    hard_failures: list[str],
) -> list[SecurityTradeIntent]:
    shelf_by_instrument = {entry.instrument_id: entry for entry in shelf}
    security_intents: list[SecurityTradeIntent] = []
    for idx, trade in enumerate(trades):
        if not _trade_has_shelf_entry(
            trade=trade,
            shelf_by_instrument=shelf_by_instrument,
            diagnostics=diagnostics,
        ):
            continue

        if not _trade_is_supported_by_shelf(
            trade=trade,
            shelf_entry=shelf_by_instrument[trade.instrument_id],
            options=options,
            diagnostics=diagnostics,
            hard_failures=hard_failures,
        ):
            continue

        intent = _build_supported_security_trade_intent(
            trade=trade,
            market_data=market_data,
            base_currency=portfolio.base_currency,
            intent_id=f"oi_{idx + 1}",
            diagnostics=diagnostics,
            hard_failures=hard_failures,
        )
        if intent is not None:
            security_intents.append(intent)
    return security_intents


def _trade_has_shelf_entry(
    *,
    trade: ProposedTrade,
    shelf_by_instrument: dict[str, ShelfEntry],
    diagnostics: DiagnosticsData,
) -> bool:
    if trade.instrument_id in shelf_by_instrument:
        return True
    diagnostics.data_quality["shelf_missing"].append(trade.instrument_id)
    return False


def _trade_is_supported_by_shelf(
    *,
    trade: ProposedTrade,
    shelf_entry: ShelfEntry,
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    hard_failures: list[str],
) -> bool:
    if trade.side != "BUY":
        return True
    if shelf_entry.status in {"SELL_ONLY", "BANNED", "SUSPENDED"}:
        _record_unsupported_shelf_trade(diagnostics=diagnostics, hard_failures=hard_failures)
        return False
    if shelf_entry.status == "RESTRICTED" and not options.allow_restricted:
        _record_unsupported_shelf_trade(diagnostics=diagnostics, hard_failures=hard_failures)
        return False
    return True


def _record_unsupported_shelf_trade(
    *, diagnostics: DiagnosticsData, hard_failures: list[str]
) -> None:
    diagnostics.warnings.append("PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF")
    hard_failures.append("PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF")


def _build_supported_security_trade_intent(
    *,
    trade: ProposedTrade,
    market_data: MarketDataSnapshot,
    base_currency: str,
    intent_id: str,
    diagnostics: DiagnosticsData,
    hard_failures: list[str],
) -> SecurityTradeIntent | None:
    intent, error_code = build_proposal_security_trade_intent(
        trade=trade,
        market_data=market_data,
        base_currency=base_currency,
        intent_id=intent_id,
        dq_log=diagnostics.data_quality,
    )
    if error_code:
        diagnostics.warnings.append(error_code)
        hard_failures.append(error_code)
    return intent


def _apply_executable_buy_intents(
    *,
    after_portfolio: PortfolioSnapshot,
    buy_intents: list[SecurityTradeIntent],
    unfunded_currencies: set[str],
    diagnostics: DiagnosticsData,
) -> list[SecurityTradeIntent]:
    executable_buy_intents: list[SecurityTradeIntent] = []
    for buy_intent in buy_intents:
        if buy_intent.notional is None:
            continue
        if buy_intent.notional.currency in unfunded_currencies:
            if "PROPOSAL_BUY_SKIPPED_UNFUNDED" not in diagnostics.warnings:
                diagnostics.warnings.append("PROPOSAL_BUY_SKIPPED_UNFUNDED")
            continue
        apply_security_trade_to_portfolio(after_portfolio, buy_intent)
        executable_buy_intents.append(buy_intent)
    return executable_buy_intents
