from decimal import Decimal
from typing import NamedTuple, cast

from src.core.advisory.alternatives_models import ProposalAlternativesConstraints
from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategy_base import BaseAlternativeStrategy
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyBuildResult,
    AlternativeStrategyInputs,
    StrategyPosition,
)
from src.core.advisory.alternatives_strategy_support import (
    decimal_string,
    estimated_notional,
    half_quantity,
    largest_sellable_position,
    preferred_buy_instrument,
    quantity_for_notional,
)


class RaiseCashRejection(NamedTuple):
    reason_code: str
    summary: str
    pivot: str
    failed_constraints: list[str] | None = None


class ReduceConcentrationRejection(NamedTuple):
    reason_code: str
    summary: str
    pivot: str
    failed_constraints: list[str] | None = None


class ReduceConcentrationPlan(NamedTuple):
    candidate: StrategyPosition
    replacement: StrategyPosition
    sell_quantity: Decimal


class ReduceConcentrationStrategy(BaseAlternativeStrategy):
    strategy_id = "reduce_concentration_v1"
    objective = "REDUCE_CONCENTRATION"
    label = "Reduce concentration"
    summary = "Sell the largest sellable holding and rotate into an approved alternative."

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        plan, rejection = reduce_concentration_plan_or_rejection(
            request=request,
            inputs=inputs,
        )
        if rejection is not None:
            return self._rejected_result(inputs=inputs, rejection=rejection)
        plan = cast(ReduceConcentrationPlan, plan)

        generated_intents, metadata = reduce_concentration_seed_payload(
            plan=plan,
            base_currency=inputs.base_currency,
        )

        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=plan.candidate.instrument_id,
                    generated_intents=generated_intents,
                    metadata=metadata,
                ),
            )
        )

    def _rejected_result(
        self,
        *,
        inputs: AlternativeStrategyInputs,
        rejection: ReduceConcentrationRejection,
    ) -> AlternativeStrategyBuildResult:
        return AlternativeStrategyBuildResult(
            rejected_candidates=(
                self._reject(
                    inputs=inputs,
                    reason_code=rejection.reason_code,
                    summary=rejection.summary,
                    pivot=rejection.pivot,
                    status="REJECTED_CONSTRAINT_VIOLATION",
                    failed_constraints=rejection.failed_constraints,
                ),
            )
        )


def reduce_concentration_plan_or_rejection(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
) -> tuple[ReduceConcentrationPlan | None, ReduceConcentrationRejection | None]:
    candidate = largest_sellable_position(inputs=inputs, constraints=request.constraints)
    if candidate is None:
        return None, ReduceConcentrationRejection(
            reason_code="ALTERNATIVE_NO_SELLABLE_HOLDING",
            summary="No sellable holding is available for concentration reduction.",
            pivot=inputs.base_currency,
            failed_constraints=["preserve_holdings", "do_not_sell"],
        )

    replacement = preferred_buy_instrument(
        inputs=inputs,
        constraints=request.constraints,
        excluded_ids={candidate.instrument_id},
        preferred_currency=inputs.base_currency,
    )
    if replacement is None:
        return None, ReduceConcentrationRejection(
            reason_code="ALTERNATIVE_NO_APPROVED_REPLACEMENT",
            summary=(
                "No approved replacement instrument is available for concentration reduction."
            ),
            pivot=candidate.instrument_id,
            failed_constraints=["restricted_instruments", "do_not_buy"],
        )

    sell_quantity = half_quantity(candidate.quantity)
    if sell_quantity is None:
        return None, ReduceConcentrationRejection(
            reason_code="ALTERNATIVE_POSITION_TOO_SMALL",
            summary=("Largest holding is too small to produce a meaningful concentration trade."),
            pivot=candidate.instrument_id,
        )
    return ReduceConcentrationPlan(candidate, replacement, sell_quantity), None


def reduce_concentration_seed_payload(
    *,
    plan: ReduceConcentrationPlan,
    base_currency: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    proceeds = estimated_notional(plan.candidate.price, plan.sell_quantity)
    generated_intents = [
        reduce_concentration_sell_intent(plan),
        reduce_concentration_buy_intent(
            plan=plan,
            base_currency=base_currency,
            proceeds=proceeds,
        ),
    ]
    return generated_intents, {
        "replacement_instrument_id": plan.replacement.instrument_id,
        "estimated_sell_notional": decimal_string(proceeds) if proceeds is not None else None,
    }


def reduce_concentration_sell_intent(
    plan: ReduceConcentrationPlan,
) -> dict[str, object]:
    return {
        "intent_type": "SECURITY_TRADE",
        "side": "SELL",
        "instrument_id": plan.candidate.instrument_id,
        "quantity": decimal_string(plan.sell_quantity),
    }


def reduce_concentration_buy_intent(
    *,
    plan: ReduceConcentrationPlan,
    base_currency: str,
    proceeds: Decimal | None,
) -> dict[str, object]:
    if proceeds is None:
        return {
            "intent_type": "SECURITY_TRADE",
            "side": "BUY",
            "instrument_id": plan.replacement.instrument_id,
            "quantity": decimal_string(plan.sell_quantity),
        }
    return {
        "intent_type": "SECURITY_TRADE",
        "side": "BUY",
        "instrument_id": plan.replacement.instrument_id,
        "notional": {
            "amount": decimal_string(proceeds),
            "currency": plan.replacement.currency or base_currency,
        },
    }


class RaiseCashStrategy(BaseAlternativeStrategy):
    strategy_id = "raise_cash_v1"
    objective = "RAISE_CASH"
    label = "Raise cash"
    summary = "Raise additional base-currency cash by selling the largest sellable holding."

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        shortfall, rejection = raise_cash_shortfall_or_rejection(
            request=request,
            inputs=inputs,
        )
        if rejection is not None:
            return self._rejected_result(inputs=inputs, rejection=rejection)

        candidate = base_currency_liquid_source(
            inputs=inputs,
            constraints=request.constraints,
        )
        if candidate is None:
            return self._rejected_result(
                inputs=inputs,
                rejection=RaiseCashRejection(
                    reason_code="ALTERNATIVE_NO_BASE_CURRENCY_LIQUID_SOURCE",
                    summary=(
                        "No sellable base-currency position can raise the requested "
                        "cash deterministically."
                    ),
                    pivot=inputs.base_currency,
                ),
            )

        candidate_price = candidate.price
        if candidate_price is None:
            return self._rejected_result(
                inputs=inputs,
                rejection=RaiseCashRejection(
                    reason_code="ALTERNATIVE_NO_BASE_CURRENCY_LIQUID_SOURCE",
                    summary=(
                        "No sellable base-currency position can raise the requested "
                        "cash deterministically."
                    ),
                    pivot=inputs.base_currency,
                ),
            )

        sell_quantity = quantity_for_notional(shortfall, candidate_price, candidate.quantity)
        if sell_quantity is None:
            return self._rejected_result(
                inputs=inputs,
                rejection=RaiseCashRejection(
                    reason_code="ALTERNATIVE_POSITION_TOO_SMALL",
                    summary=(
                        "No sellable position can raise the requested cash floor "
                        "without exceeding holdings."
                    ),
                    pivot=candidate.instrument_id,
                ),
            )

        generated_intents, metadata = raise_cash_seed_payload(
            candidate=candidate,
            sell_quantity=sell_quantity,
            shortfall=shortfall,
        )
        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=candidate.instrument_id,
                    generated_intents=generated_intents,
                    metadata=metadata,
                ),
            )
        )

    def _rejected_result(
        self,
        *,
        inputs: AlternativeStrategyInputs,
        rejection: RaiseCashRejection,
    ) -> AlternativeStrategyBuildResult:
        return AlternativeStrategyBuildResult(
            rejected_candidates=(
                self._reject(
                    inputs=inputs,
                    reason_code=rejection.reason_code,
                    summary=rejection.summary,
                    pivot=rejection.pivot,
                    status="REJECTED_CONSTRAINT_VIOLATION",
                    failed_constraints=rejection.failed_constraints,
                ),
            )
        )


def raise_cash_shortfall_or_rejection(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
) -> tuple[Decimal, RaiseCashRejection | None]:
    cash_floor = request.constraints.cash_floor
    if cash_floor is None:
        return Decimal("0"), RaiseCashRejection(
            reason_code="ALTERNATIVE_CASH_FLOOR_REQUIRED",
            summary="Cash-raising alternatives require an explicit cash floor constraint.",
            pivot=inputs.base_currency,
            failed_constraints=["cash_floor"],
        )
    if cash_floor.currency != inputs.base_currency:
        return Decimal("0"), RaiseCashRejection(
            reason_code="ALTERNATIVE_CASH_FLOOR_CURRENCY_MISMATCH",
            summary=(
                "Cash-raising alternatives currently require a cash floor "
                "in portfolio base currency."
            ),
            pivot=inputs.base_currency,
            failed_constraints=["cash_floor.currency"],
        )

    current_cash = inputs.cash_balances.get(inputs.base_currency, Decimal("0"))
    shortfall = cash_floor.amount - current_cash
    if shortfall <= Decimal("0"):
        return Decimal("0"), RaiseCashRejection(
            reason_code="ALTERNATIVE_CASH_ALREADY_SUFFICIENT",
            summary="Base-currency cash already satisfies the requested cash floor.",
            pivot=inputs.base_currency,
            failed_constraints=["cash_floor"],
        )
    return shortfall, None


def base_currency_liquid_source(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
) -> StrategyPosition | None:
    candidate = largest_sellable_position(
        inputs=inputs,
        constraints=constraints,
        preferred_currency=inputs.base_currency,
    )
    if candidate is None or candidate.price is None or candidate.currency != inputs.base_currency:
        return None
    return candidate


def raise_cash_seed_payload(
    *,
    candidate: StrategyPosition,
    sell_quantity: Decimal,
    shortfall: Decimal,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    estimated_cash_raised = estimated_notional(candidate.price, sell_quantity) or Decimal("0")
    return (
        [
            {
                "intent_type": "SECURITY_TRADE",
                "side": "SELL",
                "instrument_id": candidate.instrument_id,
                "quantity": decimal_string(sell_quantity),
            }
        ],
        {
            "cash_floor_shortfall": decimal_string(shortfall),
            "estimated_cash_raised": decimal_string(estimated_cash_raised),
        },
    )
