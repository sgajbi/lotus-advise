from abc import ABC, abstractmethod
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal
from typing import Literal

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import (
    AlternativeCandidateSeed,
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
    ProposalAlternativesConstraints,
    RejectedAlternativeCandidate,
)
from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest

_MONEY_STEP = Decimal("0.01")


class StrategyPosition(BaseModel):
    instrument_id: str = Field(description="Held instrument identifier.")
    quantity: Decimal = Field(description="Held quantity.")
    price: Decimal | None = Field(default=None, description="Last known local price.")
    currency: str | None = Field(default=None, description="Price currency when available.")


class StrategyTradeIntent(BaseModel):
    side: Literal["BUY", "SELL"] = Field(description="Baseline proposal trade side.")
    instrument_id: str = Field(description="Instrument identifier used in the baseline trade.")
    quantity: Decimal | None = Field(default=None, description="Trade quantity when available.")
    notional_amount: Decimal | None = Field(
        default=None,
        description="Trade notional amount when quantity is not available.",
    )
    notional_currency: str | None = Field(
        default=None,
        description="Trade notional currency when notional is available.",
    )


class StrategyShelfInstrument(BaseModel):
    instrument_id: str = Field(description="Shelf-backed instrument identifier.")
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"] = Field(
        description="Current shelf posture."
    )
    asset_class: str = Field(default="UNKNOWN", description="Shelf asset class.")


class AlternativeStrategyInputs(BaseModel):
    portfolio_id: str = Field(
        description="Portfolio identifier associated with the baseline proposal."
    )
    base_currency: str = Field(description="Baseline portfolio currency.")
    positions: tuple[StrategyPosition, ...] = Field(
        default=(),
        description="Deterministic ordered positions from the baseline portfolio.",
    )
    cash_balances: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Cash balances keyed by currency.",
    )
    shelf_instruments: tuple[StrategyShelfInstrument, ...] = Field(
        default=(),
        description="Deterministic ordered shelf instruments available to the strategy.",
    )
    current_proposed_trades: tuple[StrategyTradeIntent, ...] = Field(
        default=(),
        description="Deterministic ordered baseline proposed trades.",
    )

    @property
    def held_instrument_ids(self) -> tuple[str, ...]:
        return tuple(position.instrument_id for position in self.positions)

    @property
    def shelf_instrument_ids(self) -> tuple[str, ...]:
        return tuple(instrument.instrument_id for instrument in self.shelf_instruments)

    @property
    def current_trade_instrument_ids(self) -> tuple[str, ...]:
        return tuple(trade.instrument_id for trade in self.current_proposed_trades)


class AlternativeStrategyBuildResult(BaseModel):
    seeds: tuple[AlternativeCandidateSeed, ...] = Field(default=())
    rejected_candidates: tuple[RejectedAlternativeCandidate, ...] = Field(default=())


class AlternativeConstructionStrategy(ABC):
    strategy_id: str
    objective: AlternativeConstructionObjective
    required_evidence: tuple[AlternativeEvidenceRequirement, ...] = ()

    @abstractmethod
    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        """Build deterministic candidate seeds without upstream service calls."""


class _BaseStrategy(AlternativeConstructionStrategy):
    label: str
    summary: str

    def _seed(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
        pivot: str,
        generated_intents: list[dict[str, object]],
        metadata: dict[str, object] | None = None,
    ) -> AlternativeCandidateSeed:
        return AlternativeCandidateSeed(
            candidate_id=_candidate_id(
                objective=self.objective,
                portfolio_id=inputs.portfolio_id,
                pivot=pivot,
            ),
            objective=self.objective,
            strategy_id=self.strategy_id,
            status="READY_FOR_SIMULATION",
            label=self.label,
            summary=self.summary,
            required_evidence=list(self.required_evidence),
            generated_intents=generated_intents,
            metadata={
                "portfolio_id": inputs.portfolio_id,
                "base_currency": inputs.base_currency,
                "pivot_instrument_id": pivot,
                "objective_rank": request.requested_objectives.index(self.objective),
                **(metadata or {}),
            },
        )

    def _reject(
        self,
        *,
        inputs: AlternativeStrategyInputs,
        reason_code: str,
        summary: str,
        pivot: str,
        status: Literal["REJECTED_CONSTRAINT_VIOLATION", "REJECTED_INSUFFICIENT_EVIDENCE"],
        failed_constraints: list[str] | None = None,
        missing_evidence: list[str] | None = None,
    ) -> RejectedAlternativeCandidate:
        return RejectedAlternativeCandidate(
            candidate_id=_candidate_id(
                objective=self.objective,
                portfolio_id=inputs.portfolio_id,
                pivot=pivot,
            ),
            objective=self.objective,
            status=status,
            reason_code=reason_code,
            summary=summary,
            failed_constraints=failed_constraints or [],
            missing_evidence=missing_evidence or [],
            evidence_refs=[f"strategy:{self.strategy_id}", f"portfolio:{inputs.portfolio_id}"],
        )


class ReduceConcentrationStrategy(_BaseStrategy):
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
        candidate = _largest_sellable_position(inputs=inputs, constraints=request.constraints)
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

        replacement = _preferred_buy_instrument(
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

        sell_quantity = _half_quantity(candidate.quantity)
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

        proceeds = _estimated_notional(candidate.price, sell_quantity)
        generated_intents: list[dict[str, object]] = [
            {
                "intent_type": "SECURITY_TRADE",
                "side": "SELL",
                "instrument_id": candidate.instrument_id,
                "quantity": _decimal_string(sell_quantity),
            }
        ]
        if proceeds is not None:
            generated_intents.append(
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": replacement.instrument_id,
                    "notional": {
                        "amount": _decimal_string(proceeds),
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
                    "quantity": _decimal_string(sell_quantity),
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
                            _decimal_string(proceeds) if proceeds is not None else None
                        ),
                    },
                ),
            )
        )


class RaiseCashStrategy(_BaseStrategy):
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

        candidate = _largest_sellable_position(
            inputs=inputs,
            constraints=request.constraints,
            preferred_currency=inputs.base_currency,
        ) or _largest_sellable_position(inputs=inputs, constraints=request.constraints)
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

        sell_quantity = _quantity_for_notional(shortfall, candidate.price, candidate.quantity)
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

        estimated_cash_raised = _estimated_notional(candidate.price, sell_quantity) or Decimal("0")
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
                            "quantity": _decimal_string(sell_quantity),
                        }
                    ],
                    metadata={
                        "cash_floor_shortfall": _decimal_string(shortfall),
                        "estimated_cash_raised": _decimal_string(estimated_cash_raised),
                    },
                ),
            )
        )


class LowerTurnoverStrategy(_BaseStrategy):
    strategy_id = "lower_turnover_v1"
    objective = "LOWER_TURNOVER"
    label = "Lower turnover"
    summary = "Reduce turnover by trimming baseline trades while preserving intent direction."

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        baseline_trade = _first_adjustable_trade(inputs.current_proposed_trades)
        if baseline_trade is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_BASELINE_TRADE_REQUIRED",
                        summary=(
                            "Lower-turnover alternatives require an existing baseline "
                            "trade to reduce."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        reduced_trade = _reduced_trade_payload(baseline_trade)
        if reduced_trade is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_BASELINE_TRADE_TOO_SMALL",
                        summary=(
                            "Baseline trade is too small to produce a lower-turnover alternative."
                        ),
                        pivot=baseline_trade.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=baseline_trade.instrument_id,
                    generated_intents=[reduced_trade],
                    metadata={"baseline_trade_count": len(inputs.current_proposed_trades)},
                ),
            )
        )


class ImproveCurrencyAlignmentStrategy(_BaseStrategy):
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
        candidate = _largest_sellable_position(
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

        replacement = _preferred_buy_instrument(
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

        sell_quantity = _half_quantity(candidate.quantity)
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

        sell_notional = _estimated_notional(candidate.price, sell_quantity)
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
                            "quantity": _decimal_string(sell_quantity),
                        },
                        {
                            "intent_type": "SECURITY_TRADE",
                            "side": "BUY",
                            "instrument_id": replacement.instrument_id,
                            "notional": {
                                "amount": _decimal_string(sell_notional),
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


class AvoidRestrictedProductsStrategy(_BaseStrategy):
    strategy_id = "avoid_restricted_products_v1"
    objective = "AVOID_RESTRICTED_PRODUCTS"
    label = "Avoid restricted products"
    summary = (
        "Restricted-product alternatives remain deferred until canonical eligibility evidence "
        "is available."
    )
    required_evidence = ("RESTRICTED_PRODUCT_ELIGIBILITY", "MANDATE_CONTEXT")

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        missing_evidence = list(request.missing_evidence_reason_codes) or [
            "MISSING_RESTRICTED_PRODUCT_ELIGIBILITY"
        ]
        return AlternativeStrategyBuildResult(
            rejected_candidates=(
                self._reject(
                    inputs=inputs,
                    reason_code="ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE",
                    summary=(
                        "Restricted-product alternatives remain deferred until canonical "
                        "product eligibility evidence is available."
                    ),
                    pivot=inputs.base_currency,
                    status="REJECTED_INSUFFICIENT_EVIDENCE",
                    missing_evidence=missing_evidence,
                ),
            )
        )


def build_initial_strategy_registry() -> dict[
    AlternativeConstructionObjective, AlternativeConstructionStrategy
]:
    strategies: tuple[AlternativeConstructionStrategy, ...] = (
        ReduceConcentrationStrategy(),
        RaiseCashStrategy(),
        LowerTurnoverStrategy(),
        ImproveCurrencyAlignmentStrategy(),
        AvoidRestrictedProductsStrategy(),
    )
    return {strategy.objective: strategy for strategy in strategies}


def build_candidate_plan(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
    registry: dict[AlternativeConstructionObjective, AlternativeConstructionStrategy] | None = None,
) -> AlternativeStrategyBuildResult:
    strategies = registry or build_initial_strategy_registry()
    seeds: list[AlternativeCandidateSeed] = []
    rejected_candidates: list[RejectedAlternativeCandidate] = []
    for objective in request.requested_objectives:
        strategy = strategies.get(objective)
        if strategy is None:
            rejected_candidates.append(
                RejectedAlternativeCandidate(
                    candidate_id=_candidate_id(
                        objective=objective,
                        portfolio_id=inputs.portfolio_id,
                        pivot=inputs.base_currency,
                    ),
                    objective=objective,
                    status="REJECTED_CONSTRAINT_VIOLATION",
                    reason_code="ALTERNATIVE_OBJECTIVE_NOT_REGISTERED",
                    summary="Requested objective does not have a registered construction strategy.",
                    evidence_refs=[f"portfolio:{inputs.portfolio_id}"],
                )
            )
            continue
        result = strategy.build_result(request=request, inputs=inputs)
        seeds.extend(result.seeds)
        rejected_candidates.extend(result.rejected_candidates)
    return AlternativeStrategyBuildResult(
        seeds=tuple(seeds),
        rejected_candidates=tuple(rejected_candidates),
    )


def build_candidate_seeds(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
    registry: dict[AlternativeConstructionObjective, AlternativeConstructionStrategy] | None = None,
) -> tuple[AlternativeCandidateSeed, ...]:
    return build_candidate_plan(request=request, inputs=inputs, registry=registry).seeds


def _candidate_id(*, objective: str, portfolio_id: str, pivot: str) -> str:
    normalized_pivot = pivot.lower().replace("/", "_")
    return f"alt_{objective.lower()}_{portfolio_id.lower()}_{normalized_pivot}"


def _largest_sellable_position(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
    preferred_currency: str | None = None,
    exclude_currencies: set[str] | None = None,
) -> StrategyPosition | None:
    blocked_ids = set(constraints.preserve_holdings) | set(constraints.do_not_sell)
    candidates = [
        position
        for position in inputs.positions
        if position.quantity > Decimal("0")
        and position.instrument_id not in blocked_ids
        and (preferred_currency is None or position.currency == preferred_currency)
        and (exclude_currencies is None or position.currency not in exclude_currencies)
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda position: (-_position_rank_value(position), position.instrument_id),
    )[0]


def _preferred_buy_instrument(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
    excluded_ids: set[str],
    preferred_currency: str | None = None,
) -> StrategyPosition | None:
    shelf_lookup = {instrument.instrument_id: instrument for instrument in inputs.shelf_instruments}
    blocked_ids = (
        set(constraints.restricted_instruments) | set(constraints.do_not_buy) | excluded_ids
    )
    approved_positions = [
        position
        for position in inputs.positions
        if position.instrument_id in shelf_lookup
        and shelf_lookup[position.instrument_id].status == "APPROVED"
        and position.instrument_id not in blocked_ids
        and (preferred_currency is None or position.currency == preferred_currency)
    ]
    if approved_positions:
        return sorted(
            approved_positions,
            key=lambda position: (_position_rank_value(position), position.instrument_id),
        )[0]

    synthetic_positions = [
        StrategyPosition(
            instrument_id=instrument.instrument_id,
            quantity=Decimal("0"),
            price=None,
            currency=preferred_currency,
        )
        for instrument in inputs.shelf_instruments
        if instrument.status == "APPROVED" and instrument.instrument_id not in blocked_ids
    ]
    if preferred_currency is not None:
        synthetic_positions = [
            position for position in synthetic_positions if position.currency == preferred_currency
        ]
    if not synthetic_positions:
        return None
    return sorted(synthetic_positions, key=lambda position: position.instrument_id)[0]


def _first_adjustable_trade(
    trades: tuple[StrategyTradeIntent, ...],
) -> StrategyTradeIntent | None:
    for trade in trades:
        if (trade.quantity is not None and trade.quantity > Decimal("1")) or (
            trade.notional_amount is not None and trade.notional_amount > Decimal("0.01")
        ):
            return trade
    return None


def _reduced_trade_payload(trade: StrategyTradeIntent) -> dict[str, object] | None:
    if trade.quantity is not None:
        reduced_quantity = _half_quantity(trade.quantity)
        if reduced_quantity is None:
            return None
        return {
            "intent_type": "SECURITY_TRADE",
            "side": trade.side,
            "instrument_id": trade.instrument_id,
            "quantity": _decimal_string(reduced_quantity),
        }
    if trade.notional_amount is not None and trade.notional_currency is not None:
        reduced_notional = _half_money(trade.notional_amount)
        if reduced_notional is None:
            return None
        return {
            "intent_type": "SECURITY_TRADE",
            "side": trade.side,
            "instrument_id": trade.instrument_id,
            "notional": {
                "amount": _decimal_string(reduced_notional),
                "currency": trade.notional_currency,
            },
        }
    return None


def _position_rank_value(position: StrategyPosition) -> Decimal:
    if position.price is None:
        return position.quantity
    return position.quantity * position.price


def _half_quantity(quantity: Decimal) -> Decimal | None:
    if quantity <= Decimal("1"):
        return None
    halved = quantity / Decimal("2")
    reduced = halved.quantize(Decimal("1"), rounding=ROUND_DOWN)
    if reduced <= Decimal("0"):
        return None
    return reduced


def _half_money(amount: Decimal) -> Decimal | None:
    if amount <= _MONEY_STEP:
        return None
    halved = (amount / Decimal("2")).quantize(_MONEY_STEP, rounding=ROUND_HALF_UP)
    if halved <= Decimal("0"):
        return None
    return halved


def _estimated_notional(price: Decimal | None, quantity: Decimal) -> Decimal | None:
    if price is None:
        return None
    return (price * quantity).quantize(_MONEY_STEP, rounding=ROUND_HALF_UP)


def _quantity_for_notional(
    required_notional: Decimal,
    price: Decimal,
    max_quantity: Decimal,
) -> Decimal | None:
    if required_notional <= Decimal("0"):
        return None
    required_quantity = (required_notional / price).quantize(Decimal("1"), rounding=ROUND_UP)
    if required_quantity <= Decimal("0") or required_quantity > max_quantity:
        return None
    return required_quantity


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")
