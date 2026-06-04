from decimal import Decimal

from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategy_base import BaseAlternativeStrategy
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyBuildResult,
    AlternativeStrategyInputs,
)
from src.core.advisory.alternatives_strategy_support import (
    decimal_string,
    estimated_notional,
    half_quantity,
    largest_sellable_position,
    preferred_buy_instrument,
    quantity_for_notional,
)


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
        candidate = largest_sellable_position(inputs=inputs, constraints=request.constraints)
        if candidate is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_NO_SELLABLE_HOLDING",
                        summary="No sellable holding is available for concentration reduction.",
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                        failed_constraints=["preserve_holdings", "do_not_sell"],
                    ),
                )
            )

        replacement = preferred_buy_instrument(
            inputs=inputs,
            constraints=request.constraints,
            excluded_ids={candidate.instrument_id},
            preferred_currency=inputs.base_currency,
        )
        if replacement is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_NO_APPROVED_REPLACEMENT",
                        summary=(
                            "No approved replacement instrument is available for "
                            "concentration reduction."
                        ),
                        pivot=candidate.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                        failed_constraints=["restricted_instruments", "do_not_buy"],
                    ),
                )
            )

        sell_quantity = half_quantity(candidate.quantity)
        if sell_quantity is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_POSITION_TOO_SMALL",
                        summary=(
                            "Largest holding is too small to produce a meaningful "
                            "concentration trade."
                        ),
                        pivot=candidate.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        proceeds = estimated_notional(candidate.price, sell_quantity)
        generated_intents: list[dict[str, object]] = [
            {
                "intent_type": "SECURITY_TRADE",
                "side": "SELL",
                "instrument_id": candidate.instrument_id,
                "quantity": decimal_string(sell_quantity),
            }
        ]
        if proceeds is not None:
            generated_intents.append(
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": replacement.instrument_id,
                    "notional": {
                        "amount": decimal_string(proceeds),
                        "currency": replacement.currency or inputs.base_currency,
                    },
                }
            )
        else:
            generated_intents.append(
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": replacement.instrument_id,
                    "quantity": decimal_string(sell_quantity),
                }
            )

        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=candidate.instrument_id,
                    generated_intents=generated_intents,
                    metadata={
                        "replacement_instrument_id": replacement.instrument_id,
                        "estimated_sell_notional": (
                            decimal_string(proceeds) if proceeds is not None else None
                        ),
                    },
                ),
            )
        )


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
        if request.constraints.cash_floor is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_CASH_FLOOR_REQUIRED",
                        summary=(
                            "Cash-raising alternatives require an explicit cash floor constraint."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                        failed_constraints=["cash_floor"],
                    ),
                )
            )
        if request.constraints.cash_floor.currency != inputs.base_currency:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_CASH_FLOOR_CURRENCY_MISMATCH",
                        summary=(
                            "Cash-raising alternatives currently require a cash floor "
                            "in portfolio base currency."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                        failed_constraints=["cash_floor.currency"],
                    ),
                )
            )

        current_cash = inputs.cash_balances.get(inputs.base_currency, Decimal("0"))
        shortfall = request.constraints.cash_floor.amount - current_cash
        if shortfall <= Decimal("0"):
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_CASH_ALREADY_SUFFICIENT",
                        summary="Base-currency cash already satisfies the requested cash floor.",
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                        failed_constraints=["cash_floor"],
                    ),
                )
            )

        candidate = largest_sellable_position(
            inputs=inputs,
            constraints=request.constraints,
            preferred_currency=inputs.base_currency,
        ) or largest_sellable_position(inputs=inputs, constraints=request.constraints)
        if (
            candidate is None
            or candidate.price is None
            or candidate.currency != inputs.base_currency
        ):
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_NO_BASE_CURRENCY_LIQUID_SOURCE",
                        summary=(
                            "No sellable base-currency position can raise the requested "
                            "cash deterministically."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        sell_quantity = quantity_for_notional(shortfall, candidate.price, candidate.quantity)
        if sell_quantity is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_POSITION_TOO_SMALL",
                        summary=(
                            "No sellable position can raise the requested cash floor "
                            "without exceeding holdings."
                        ),
                        pivot=candidate.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        estimated_cash_raised = estimated_notional(candidate.price, sell_quantity) or Decimal("0")
        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=candidate.instrument_id,
                    generated_intents=[
                        {
                            "intent_type": "SECURITY_TRADE",
                            "side": "SELL",
                            "instrument_id": candidate.instrument_id,
                            "quantity": decimal_string(sell_quantity),
                        }
                    ],
                    metadata={
                        "cash_floor_shortfall": decimal_string(shortfall),
                        "estimated_cash_raised": decimal_string(estimated_cash_raised),
                    },
                ),
            )
        )
