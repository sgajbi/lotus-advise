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
)


class ImproveCurrencyAlignmentStrategy(BaseAlternativeStrategy):
    strategy_id = "improve_currency_alignment_v1"
    objective = "IMPROVE_CURRENCY_ALIGNMENT"
    label = "Improve currency alignment"
    summary = "Rotate a non-base-currency holding into an approved base-currency instrument."

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        if request.constraints.allow_fx is False:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_FX_ACTIONS_NOT_PERMITTED",
                        summary=(
                            "Currency-alignment alternatives require FX-permitted trading posture."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                        failed_constraints=["allow_fx"],
                    ),
                )
            )

        aligned_currencies = (
            tuple(request.constraints.allowed_currencies)
            if request.constraints.allowed_currencies
            else (inputs.base_currency,)
        )
        candidate = largest_sellable_position(
            inputs=inputs,
            constraints=request.constraints,
            exclude_currencies=set(aligned_currencies),
        )
        if candidate is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_NO_MISALIGNED_HOLDING",
                        summary=(
                            "Portfolio does not contain a sellable holding outside the "
                            "allowed currency set."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
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
                        reason_code="ALTERNATIVE_NO_ALIGNED_REPLACEMENT",
                        summary=(
                            "No approved base-currency replacement instrument is "
                            "available for currency alignment."
                        ),
                        pivot=candidate.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
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
                            "Foreign-currency holding is too small to produce a "
                            "meaningful alignment trade."
                        ),
                        pivot=candidate.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        sell_notional = estimated_notional(candidate.price, sell_quantity)
        if sell_notional is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_PRICE_REQUIRED_FOR_ALIGNMENT",
                        summary=(
                            "Currency-alignment alternatives require price evidence "
                            "for the selected holding."
                        ),
                        pivot=candidate.instrument_id,
                        status="REJECTED_INSUFFICIENT_EVIDENCE",
                    ),
                )
            )

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
                        },
                        {
                            "intent_type": "SECURITY_TRADE",
                            "side": "BUY",
                            "instrument_id": replacement.instrument_id,
                            "notional": {
                                "amount": decimal_string(sell_notional),
                                "currency": replacement.currency or inputs.base_currency,
                            },
                        },
                    ],
                    metadata={
                        "replacement_instrument_id": replacement.instrument_id,
                        "from_currency": candidate.currency,
                        "to_currency": replacement.currency or inputs.base_currency,
                    },
                ),
            )
        )
