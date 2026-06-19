from collections.abc import Mapping, Sequence
from typing import TypeAlias

from src.core.order_intent_models import FxSpotIntent, SecurityTradeIntent

ProposalIntent: TypeAlias = SecurityTradeIntent | FxSpotIntent


def link_buy_intent_dependencies(
    intents: Sequence[ProposalIntent],
    *,
    fx_intent_id_by_currency: Mapping[str, str] | None = None,
    include_same_currency_sell_dependency: bool = False,
) -> None:
    """Attach deterministic dependencies to BUY security intents in-place."""
    fx_dependencies = dict(fx_intent_id_by_currency or {})
    sell_intent_id_by_currency = _sell_intent_id_by_currency(
        intents,
        include_same_currency_sell_dependency=include_same_currency_sell_dependency,
    )

    for intent in _buy_security_intents_with_notional(intents):
        notional = intent.notional
        if notional is None:
            continue
        currency = notional.currency
        _append_dependency(intent, fx_dependencies.get(currency))

        if include_same_currency_sell_dependency:
            _append_dependency(intent, sell_intent_id_by_currency.get(currency))


def _sell_intent_id_by_currency(
    intents: Sequence[ProposalIntent],
    *,
    include_same_currency_sell_dependency: bool,
) -> dict[str, str]:
    if not include_same_currency_sell_dependency:
        return {}
    sell_intent_id_by_currency: dict[str, str] = {}
    for intent in _sell_security_intents_with_notional(intents):
        notional = intent.notional
        if notional is not None:
            sell_intent_id_by_currency[notional.currency] = intent.intent_id
    return sell_intent_id_by_currency


def _sell_security_intents_with_notional(
    intents: Sequence[ProposalIntent],
) -> list[SecurityTradeIntent]:
    return [
        intent
        for intent in intents
        if intent.intent_type == "SECURITY_TRADE"
        and intent.side == "SELL"
        and intent.notional is not None
    ]


def _buy_security_intents_with_notional(
    intents: Sequence[ProposalIntent],
) -> list[SecurityTradeIntent]:
    return [
        intent
        for intent in intents
        if intent.intent_type == "SECURITY_TRADE"
        and intent.side == "BUY"
        and intent.notional is not None
    ]


def _append_dependency(intent: SecurityTradeIntent, dependency: str | None) -> None:
    if dependency is not None and dependency not in intent.dependencies:
        intent.dependencies.append(dependency)
