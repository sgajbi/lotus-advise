from decimal import Decimal
from typing import Literal, NamedTuple, cast

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
)


class CurrencyAlignmentRejection(NamedTuple):
    reason_code: str
    summary: str
    pivot: str
    status: Literal["REJECTED_CONSTRAINT_VIOLATION", "REJECTED_INSUFFICIENT_EVIDENCE"]
    failed_constraints: list[str] | None = None


class CurrencyAlignmentTradePlan(NamedTuple):
    candidate: StrategyPosition
    generated_intents: list[dict[str, object]]
    metadata: dict[str, object]


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
        plan, rejection = currency_alignment_trade_plan_or_rejection(
            request=request,
            inputs=inputs,
        )
        if rejection is not None:
            return self._rejected_result(inputs=inputs, rejection=rejection)
        plan = cast(CurrencyAlignmentTradePlan, plan)

        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=plan.candidate.instrument_id,
                    generated_intents=plan.generated_intents,
                    metadata=plan.metadata,
                ),
            )
        )

    def _rejected_result(
        self,
        *,
        inputs: AlternativeStrategyInputs,
        rejection: CurrencyAlignmentRejection,
    ) -> AlternativeStrategyBuildResult:
        return AlternativeStrategyBuildResult(
            rejected_candidates=(
                self._reject(
                    inputs=inputs,
                    reason_code=rejection.reason_code,
                    summary=rejection.summary,
                    pivot=rejection.pivot,
                    status=rejection.status,
                    failed_constraints=rejection.failed_constraints,
                ),
            )
        )


def currency_alignment_trade_plan_or_rejection(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
) -> tuple[CurrencyAlignmentTradePlan | None, CurrencyAlignmentRejection | None]:
    precondition_rejection = currency_alignment_precondition_rejection(
        request=request,
        inputs=inputs,
    )
    if precondition_rejection is not None:
        return None, precondition_rejection

    candidate = misaligned_currency_position(inputs=inputs, constraints=request.constraints)
    if candidate is None:
        return None, no_misaligned_holding_rejection(inputs)

    replacement = currency_alignment_replacement(
        inputs=inputs,
        constraints=request.constraints,
        candidate=candidate,
    )
    if replacement is None:
        return None, no_aligned_replacement_rejection(candidate)

    return currency_alignment_trade_plan(
        inputs=inputs,
        candidate=candidate,
        replacement=replacement,
    )


def currency_alignment_precondition_rejection(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
) -> CurrencyAlignmentRejection | None:
    if request.constraints.allow_fx is not False:
        return None
    return CurrencyAlignmentRejection(
        reason_code="ALTERNATIVE_FX_ACTIONS_NOT_PERMITTED",
        summary="Currency-alignment alternatives require FX-permitted trading posture.",
        pivot=inputs.base_currency,
        status="REJECTED_CONSTRAINT_VIOLATION",
        failed_constraints=["allow_fx"],
    )


def misaligned_currency_position(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
) -> StrategyPosition | None:
    return largest_sellable_position(
        inputs=inputs,
        constraints=constraints,
        exclude_currencies=set(aligned_currency_set(inputs=inputs, constraints=constraints)),
    )


def aligned_currency_set(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
) -> tuple[str, ...]:
    return tuple(constraints.allowed_currencies) or (inputs.base_currency,)


def currency_alignment_replacement(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
    candidate: StrategyPosition,
) -> StrategyPosition | None:
    return preferred_buy_instrument(
        inputs=inputs,
        constraints=constraints,
        excluded_ids={candidate.instrument_id},
        preferred_currency=inputs.base_currency,
    )


def currency_alignment_trade_plan(
    *,
    inputs: AlternativeStrategyInputs,
    candidate: StrategyPosition,
    replacement: StrategyPosition,
) -> tuple[CurrencyAlignmentTradePlan | None, CurrencyAlignmentRejection | None]:
    sell_quantity = half_quantity(candidate.quantity)
    if sell_quantity is None:
        return None, position_too_small_rejection(candidate)

    sell_notional = estimated_notional(candidate.price, sell_quantity)
    if sell_notional is None:
        return None, alignment_price_required_rejection(candidate)

    return (
        CurrencyAlignmentTradePlan(
            candidate=candidate,
            generated_intents=currency_alignment_intents(
                inputs=inputs,
                candidate=candidate,
                replacement=replacement,
                sell_quantity=sell_quantity,
                sell_notional=sell_notional,
            ),
            metadata=currency_alignment_metadata(
                inputs=inputs,
                candidate=candidate,
                replacement=replacement,
            ),
        ),
        None,
    )


def currency_alignment_intents(
    *,
    inputs: AlternativeStrategyInputs,
    candidate: StrategyPosition,
    replacement: StrategyPosition,
    sell_quantity: Decimal,
    sell_notional: Decimal,
) -> list[dict[str, object]]:
    return [
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
    ]


def currency_alignment_metadata(
    *,
    inputs: AlternativeStrategyInputs,
    candidate: StrategyPosition,
    replacement: StrategyPosition,
) -> dict[str, object]:
    return {
        "replacement_instrument_id": replacement.instrument_id,
        "from_currency": candidate.currency,
        "to_currency": replacement.currency or inputs.base_currency,
    }


def no_misaligned_holding_rejection(
    inputs: AlternativeStrategyInputs,
) -> CurrencyAlignmentRejection:
    return CurrencyAlignmentRejection(
        reason_code="ALTERNATIVE_NO_MISALIGNED_HOLDING",
        summary=("Portfolio does not contain a sellable holding outside the allowed currency set."),
        pivot=inputs.base_currency,
        status="REJECTED_CONSTRAINT_VIOLATION",
    )


def no_aligned_replacement_rejection(
    candidate: StrategyPosition,
) -> CurrencyAlignmentRejection:
    return CurrencyAlignmentRejection(
        reason_code="ALTERNATIVE_NO_ALIGNED_REPLACEMENT",
        summary=(
            "No approved base-currency replacement instrument is available for currency alignment."
        ),
        pivot=candidate.instrument_id,
        status="REJECTED_CONSTRAINT_VIOLATION",
    )


def position_too_small_rejection(candidate: StrategyPosition) -> CurrencyAlignmentRejection:
    return CurrencyAlignmentRejection(
        reason_code="ALTERNATIVE_POSITION_TOO_SMALL",
        summary=("Foreign-currency holding is too small to produce a meaningful alignment trade."),
        pivot=candidate.instrument_id,
        status="REJECTED_CONSTRAINT_VIOLATION",
    )


def alignment_price_required_rejection(candidate: StrategyPosition) -> CurrencyAlignmentRejection:
    return CurrencyAlignmentRejection(
        reason_code="ALTERNATIVE_PRICE_REQUIRED_FOR_ALIGNMENT",
        summary=(
            "Currency-alignment alternatives require price evidence for the selected holding."
        ),
        pivot=candidate.instrument_id,
        status="REJECTED_INSUFFICIENT_EVIDENCE",
    )
