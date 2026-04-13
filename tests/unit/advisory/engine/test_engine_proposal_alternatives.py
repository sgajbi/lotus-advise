from decimal import Decimal

import pytest

from src.core.advisory import (
    AlternativesRequestNormalizationError,
    AlternativeStrategyInputs,
    ProposalAlternativesConstraints,
    ProposalAlternativesRequest,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
    build_candidate_plan,
    build_candidate_seeds,
    normalize_alternatives_request,
)
from src.core.advisory.alternatives_strategies import (
    _estimated_notional,
    _first_adjustable_trade,
    _half_money,
    _half_quantity,
    _largest_sellable_position,
    _position_rank_value,
    _preferred_buy_instrument,
    _quantity_for_notional,
    _reduced_trade_payload,
)


def _inputs() -> AlternativeStrategyInputs:
    return AlternativeStrategyInputs(
        portfolio_id="pf_demo",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="AAPL",
                quantity=Decimal("100"),
                price=Decimal("150"),
                currency="USD",
            ),
            StrategyPosition(
                instrument_id="SAP",
                quantity=Decimal("80"),
                price=Decimal("120"),
                currency="EUR",
            ),
            StrategyPosition(
                instrument_id="MSFT",
                quantity=Decimal("50"),
                price=Decimal("100"),
                currency="USD",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(
            StrategyShelfInstrument(instrument_id="AAPL", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="MSFT", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="NVDA", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="SAP", status="APPROVED"),
        ),
        current_proposed_trades=(
            StrategyTradeIntent(side="BUY", instrument_id="NVDA", quantity=Decimal("20")),
            StrategyTradeIntent(side="SELL", instrument_id="AAPL", quantity=Decimal("10")),
        ),
    )


def _normalized(
    *,
    objectives: list[str],
    constraints: dict[str, object] | None = None,
    selection_mode: str = "generation",
):
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=objectives,
            constraints=constraints or {},
        ),
        selection_mode=selection_mode,
    )
    assert normalized is not None
    return normalized


def test_normalize_alternatives_request_rejects_deferred_objective():
    request = ProposalAlternativesRequest(objectives=["REBALANCE_TO_REFERENCE_MODEL"])

    with pytest.raises(AlternativesRequestNormalizationError) as exc_info:
        normalize_alternatives_request(request)

    assert exc_info.value.reason_code == "ALTERNATIVES_OBJECTIVE_NOT_SUPPORTED"
    assert exc_info.value.details == {"deferred_objectives": ["REBALANCE_TO_REFERENCE_MODEL"]}


def test_normalize_alternatives_request_rejects_selected_alternative_on_generation():
    request = ProposalAlternativesRequest(
        objectives=["REDUCE_CONCENTRATION"],
        selected_alternative_id="alt_reduce_concentration_pf_aapl",
    )

    with pytest.raises(AlternativesRequestNormalizationError) as exc_info:
        normalize_alternatives_request(request)

    assert exc_info.value.reason_code == "ALTERNATIVES_SELECTION_NOT_ALLOWED_ON_GENERATION"


def test_normalize_alternatives_request_handles_disabled_and_missing_objectives():
    assert (
        normalize_alternatives_request(
            ProposalAlternativesRequest(enabled=False, objectives=["REDUCE_CONCENTRATION"])
        )
        is None
    )

    with pytest.raises(AlternativesRequestNormalizationError) as exc_info:
        normalize_alternatives_request(ProposalAlternativesRequest(objectives=[]))

    assert exc_info.value.reason_code == "ALTERNATIVES_OBJECTIVES_REQUIRED"


def test_normalize_alternatives_request_flags_missing_evidence_for_conditional_scope():
    request = ProposalAlternativesRequest(
        objectives=["AVOID_RESTRICTED_PRODUCTS"],
        constraints={"mandate_restrictions": {"restricted_product_exception": False}},
    )

    normalized = normalize_alternatives_request(request, selection_mode="selection")

    assert normalized is not None
    assert normalized.requested_objectives == ("AVOID_RESTRICTED_PRODUCTS",)
    assert normalized.missing_evidence_reason_codes == (
        "MISSING_RESTRICTED_PRODUCT_ELIGIBILITY",
        "MISSING_MANDATE_CONTEXT",
    )


def test_normalize_alternatives_request_flags_missing_client_preferences_when_required():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=["REDUCE_CONCENTRATION"],
            constraints={"client_preferences": {"avoid_tobacco": True}},
        ),
        selection_mode="selection",
    )

    assert normalized is not None
    assert normalized.missing_evidence_reason_codes == ("MISSING_CLIENT_PREFERENCES",)


def test_normalize_alternatives_request_enforces_first_implementation_bound():
    request = ProposalAlternativesRequest(
        objectives=["REDUCE_CONCENTRATION"],
        max_alternatives=4,
    )

    with pytest.raises(AlternativesRequestNormalizationError) as exc_info:
        normalize_alternatives_request(request)

    assert exc_info.value.reason_code == "ALTERNATIVES_MAX_LIMIT_EXCEEDED"


def test_build_candidate_seeds_is_deterministic_and_objective_ordered():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=[
                "LOWER_TURNOVER",
                "REDUCE_CONCENTRATION",
                "IMPROVE_CURRENCY_ALIGNMENT",
            ]
        )
    )
    assert normalized is not None

    first = build_candidate_seeds(request=normalized, inputs=_inputs())
    second = build_candidate_seeds(request=normalized, inputs=_inputs())

    assert [seed.objective for seed in first] == [
        "LOWER_TURNOVER",
        "REDUCE_CONCENTRATION",
        "IMPROVE_CURRENCY_ALIGNMENT",
    ]
    assert [seed.candidate_id for seed in first] == [seed.candidate_id for seed in second]
    assert first[0].generated_intents[0]["instrument_id"] == "NVDA"
    assert first[1].metadata["replacement_instrument_id"] == "MSFT"
    assert first[2].metadata["from_currency"] == "EUR"


def test_build_candidate_plan_generates_reduce_concentration_and_alignment_trades():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=["REDUCE_CONCENTRATION", "IMPROVE_CURRENCY_ALIGNMENT"]
        )
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.rejected_candidates == ()
    assert len(result.seeds) == 2

    concentration_seed = result.seeds[0]
    assert concentration_seed.generated_intents[0] == {
        "intent_type": "SECURITY_TRADE",
        "side": "SELL",
        "instrument_id": "AAPL",
        "quantity": "50",
    }
    assert concentration_seed.generated_intents[1]["side"] == "BUY"
    assert concentration_seed.generated_intents[1]["instrument_id"] == "MSFT"
    assert concentration_seed.generated_intents[1]["notional"] == {
        "amount": "7500",
        "currency": "USD",
    }

    alignment_seed = result.seeds[1]
    assert alignment_seed.generated_intents[0]["instrument_id"] == "SAP"
    assert alignment_seed.generated_intents[1]["instrument_id"] == "MSFT"
    assert alignment_seed.generated_intents[1]["notional"]["currency"] == "USD"


def test_build_candidate_plan_generates_cash_raise_from_cash_floor_shortfall():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=["RAISE_CASH"],
            constraints={"cash_floor": {"amount": "2500", "currency": "USD"}},
        )
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.rejected_candidates == ()
    assert len(result.seeds) == 1
    seed = result.seeds[0]
    assert seed.generated_intents == [
        {
            "intent_type": "SECURITY_TRADE",
            "side": "SELL",
            "instrument_id": "AAPL",
            "quantity": "10",
        }
    ]
    assert seed.metadata["cash_floor_shortfall"] == "1500"
    assert seed.metadata["estimated_cash_raised"] == "1500"


def test_build_candidate_plan_rejects_raise_cash_without_valid_cash_floor():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(objectives=["RAISE_CASH"])
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.seeds == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_CASH_FLOOR_REQUIRED"


def test_build_candidate_plan_reduces_baseline_trade_turnover():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(objectives=["LOWER_TURNOVER"])
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.rejected_candidates == ()
    assert len(result.seeds) == 1
    assert result.seeds[0].generated_intents == [
        {
            "intent_type": "SECURITY_TRADE",
            "side": "BUY",
            "instrument_id": "NVDA",
            "quantity": "10",
        }
    ]


def test_build_candidate_plan_rejects_when_only_preserved_holdings_remain_sellable():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=["REDUCE_CONCENTRATION"],
            constraints={"preserve_holdings": ["AAPL", "SAP", "MSFT"]},
        )
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.seeds == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_NO_SELLABLE_HOLDING"


def test_build_candidate_plan_rejects_currency_alignment_when_fx_not_allowed():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(
            objectives=["IMPROVE_CURRENCY_ALIGNMENT"],
            constraints={"allow_fx": False},
        )
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.seeds == ()
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_FX_ACTIONS_NOT_PERMITTED"


def test_build_candidate_plan_explicitly_defers_avoid_restricted_products_without_evidence():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(objectives=["AVOID_RESTRICTED_PRODUCTS"]),
        selection_mode="selection",
    )
    assert normalized is not None

    result = build_candidate_plan(request=normalized, inputs=_inputs())

    assert result.seeds == ()
    assert len(result.rejected_candidates) == 1
    assert (
        result.rejected_candidates[0].reason_code
        == "ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE"
    )


def test_build_candidate_plan_rejects_reduce_concentration_without_approved_replacement():
    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_no_replacement",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="AAPL",
                quantity=Decimal("100"),
                price=Decimal("150"),
                currency="USD",
            ),
            StrategyPosition(
                instrument_id="SAP",
                quantity=Decimal("80"),
                price=Decimal("120"),
                currency="EUR",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(
            StrategyShelfInstrument(instrument_id="AAPL", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="SAP", status="RESTRICTED"),
        ),
        current_proposed_trades=(),
    )

    result = build_candidate_plan(
        request=_normalized(
            objectives=["REDUCE_CONCENTRATION"],
            constraints={"do_not_buy": ["SAP"]},
        ),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_NO_APPROVED_REPLACEMENT"


def test_build_candidate_plan_rejects_reduce_concentration_when_position_too_small():
    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_small_reduce",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="AAPL",
                quantity=Decimal("1"),
                price=Decimal("150"),
                currency="USD",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(
            StrategyShelfInstrument(instrument_id="AAPL", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="MSFT", status="APPROVED"),
        ),
        current_proposed_trades=(),
    )

    result = build_candidate_plan(
        request=_normalized(objectives=["REDUCE_CONCENTRATION"]),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_POSITION_TOO_SMALL"


def test_build_candidate_plan_reduce_concentration_falls_back_to_quantity_when_price_missing():
    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_reduce_no_price",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="AAPL",
                quantity=Decimal("10000"),
                price=None,
                currency="USD",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(
            StrategyShelfInstrument(instrument_id="AAPL", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="NVDA", status="APPROVED"),
        ),
        current_proposed_trades=(),
    )

    result = build_candidate_plan(
        request=_normalized(objectives=["REDUCE_CONCENTRATION"]),
        inputs=inputs,
    )

    assert result.rejected_candidates == ()
    assert result.seeds[0].generated_intents[1] == {
        "intent_type": "SECURITY_TRADE",
        "side": "BUY",
        "instrument_id": "NVDA",
        "quantity": "5000",
    }


def test_build_candidate_plan_rejects_raise_cash_for_currency_mismatch_and_sufficient_cash():
    mismatch_result = build_candidate_plan(
        request=_normalized(
            objectives=["RAISE_CASH"],
            constraints={"cash_floor": {"amount": "2500", "currency": "EUR"}},
        ),
        inputs=_inputs(),
    )
    assert mismatch_result.rejected_candidates[0].reason_code == (
        "ALTERNATIVE_CASH_FLOOR_CURRENCY_MISMATCH"
    )

    sufficient_cash_inputs = _inputs().model_copy(
        update={"cash_balances": {"USD": Decimal("5000")}},
        deep=True,
    )
    sufficient_result = build_candidate_plan(
        request=_normalized(
            objectives=["RAISE_CASH"],
            constraints={"cash_floor": {"amount": "2500", "currency": "USD"}},
        ),
        inputs=sufficient_cash_inputs,
    )
    assert sufficient_result.rejected_candidates[0].reason_code == (
        "ALTERNATIVE_CASH_ALREADY_SUFFICIENT"
    )


def test_build_candidate_plan_rejects_raise_cash_without_base_currency_liquid_source():
    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_raise_cash_no_usd",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="SAP",
                quantity=Decimal("80"),
                price=Decimal("120"),
                currency="EUR",
            ),
        ),
        cash_balances={"USD": Decimal("100")},
        shelf_instruments=(StrategyShelfInstrument(instrument_id="SAP", status="APPROVED"),),
        current_proposed_trades=(),
    )

    result = build_candidate_plan(
        request=_normalized(
            objectives=["RAISE_CASH"],
            constraints={"cash_floor": {"amount": "2500", "currency": "USD"}},
        ),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_NO_BASE_CURRENCY_LIQUID_SOURCE"


def test_build_candidate_plan_rejects_raise_cash_when_shortfall_exceeds_holdings():
    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_raise_cash_small",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="AAPL",
                quantity=Decimal("10"),
                price=Decimal("100"),
                currency="USD",
            ),
        ),
        cash_balances={"USD": Decimal("100")},
        shelf_instruments=(StrategyShelfInstrument(instrument_id="AAPL", status="APPROVED"),),
        current_proposed_trades=(),
    )

    result = build_candidate_plan(
        request=_normalized(
            objectives=["RAISE_CASH"],
            constraints={"cash_floor": {"amount": "5000", "currency": "USD"}},
        ),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_POSITION_TOO_SMALL"


def test_build_candidate_plan_rejects_lower_turnover_without_adjustable_trade():
    inputs = _inputs().model_copy(update={"current_proposed_trades": ()}, deep=True)

    result = build_candidate_plan(
        request=_normalized(objectives=["LOWER_TURNOVER"]),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_BASELINE_TRADE_REQUIRED"


def test_build_candidate_plan_rejects_lower_turnover_when_trade_too_small():
    inputs = _inputs().model_copy(
        update={
            "current_proposed_trades": (
                StrategyTradeIntent(side="BUY", instrument_id="NVDA", quantity=Decimal("1.5")),
            )
        },
        deep=True,
    )

    result = build_candidate_plan(
        request=_normalized(objectives=["LOWER_TURNOVER"]),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_BASELINE_TRADE_TOO_SMALL"


def test_build_candidate_plan_rejects_currency_alignment_without_misaligned_holding():
    inputs = _inputs().model_copy(
        update={
            "positions": (
                StrategyPosition(
                    instrument_id="AAPL",
                    quantity=Decimal("100"),
                    price=Decimal("150"),
                    currency="USD",
                ),
                StrategyPosition(
                    instrument_id="MSFT",
                    quantity=Decimal("50"),
                    price=Decimal("100"),
                    currency="USD",
                ),
            )
        },
        deep=True,
    )

    result = build_candidate_plan(
        request=_normalized(objectives=["IMPROVE_CURRENCY_ALIGNMENT"]),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_NO_MISALIGNED_HOLDING"


def test_build_candidate_plan_rejects_currency_alignment_without_aligned_replacement():
    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_alignment_no_replacement",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="SAP",
                quantity=Decimal("80"),
                price=Decimal("120"),
                currency="EUR",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(StrategyShelfInstrument(instrument_id="SAP", status="APPROVED"),),
        current_proposed_trades=(),
    )

    result = build_candidate_plan(
        request=_normalized(objectives=["IMPROVE_CURRENCY_ALIGNMENT"]),
        inputs=inputs,
    )

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_NO_ALIGNED_REPLACEMENT"


def test_build_candidate_plan_rejects_currency_alignment_for_small_or_unpriced_position():
    small_inputs = AlternativeStrategyInputs(
        portfolio_id="pf_alignment_small",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="SAP",
                quantity=Decimal("1"),
                price=Decimal("120"),
                currency="EUR",
            ),
            StrategyPosition(
                instrument_id="MSFT",
                quantity=Decimal("50"),
                price=Decimal("100"),
                currency="USD",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(
            StrategyShelfInstrument(instrument_id="SAP", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="MSFT", status="APPROVED"),
        ),
        current_proposed_trades=(),
    )
    small_result = build_candidate_plan(
        request=_normalized(objectives=["IMPROVE_CURRENCY_ALIGNMENT"]),
        inputs=small_inputs,
    )
    assert small_result.rejected_candidates[0].reason_code == "ALTERNATIVE_POSITION_TOO_SMALL"

    unpriced_inputs = AlternativeStrategyInputs(
        portfolio_id="pf_alignment_unpriced",
        base_currency="USD",
        positions=(
            StrategyPosition(
                instrument_id="SAP",
                quantity=Decimal("80"),
                price=None,
                currency="EUR",
            ),
            StrategyPosition(
                instrument_id="MSFT",
                quantity=Decimal("50"),
                price=Decimal("100"),
                currency="USD",
            ),
        ),
        cash_balances={"USD": Decimal("1000")},
        shelf_instruments=(
            StrategyShelfInstrument(instrument_id="SAP", status="APPROVED"),
            StrategyShelfInstrument(instrument_id="MSFT", status="APPROVED"),
        ),
        current_proposed_trades=(),
    )
    unpriced_result = build_candidate_plan(
        request=_normalized(objectives=["IMPROVE_CURRENCY_ALIGNMENT"]),
        inputs=unpriced_inputs,
    )
    assert unpriced_result.rejected_candidates[0].reason_code == (
        "ALTERNATIVE_PRICE_REQUIRED_FOR_ALIGNMENT"
    )


def test_build_candidate_plan_rejects_unregistered_objective_when_registry_missing():
    normalized = _normalized(objectives=["REDUCE_CONCENTRATION"])
    registry = {"LOWER_TURNOVER": object()}

    result = build_candidate_plan(request=normalized, inputs=_inputs(), registry=registry)

    assert result.seeds == ()
    assert result.rejected_candidates[0].reason_code == "ALTERNATIVE_OBJECTIVE_NOT_REGISTERED"


def test_alternatives_helper_functions_cover_money_and_trade_edge_cases():
    assert _position_rank_value(
        StrategyPosition(
            instrument_id="AAPL",
            quantity=Decimal("2"),
            price=None,
            currency="USD",
        )
    ) == Decimal("2")
    assert _half_quantity(Decimal("1")) is None
    assert _half_quantity(Decimal("5")) == Decimal("2")
    assert _half_money(Decimal("0.01")) is None
    assert _half_money(Decimal("5.00")) == Decimal("2.50")
    assert _estimated_notional(None, Decimal("5")) is None
    assert _estimated_notional(Decimal("10"), Decimal("5")) == Decimal("50.00")
    assert _quantity_for_notional(Decimal("0"), Decimal("10"), Decimal("5")) is None
    assert _quantity_for_notional(Decimal("75"), Decimal("10"), Decimal("5")) is None
    assert _quantity_for_notional(Decimal("50"), Decimal("10"), Decimal("5")) == Decimal("5")

    notional_trade = StrategyTradeIntent(
        side="BUY",
        instrument_id="NVDA",
        notional_amount=Decimal("100.00"),
        notional_currency="USD",
    )
    assert _first_adjustable_trade((notional_trade,)) == notional_trade
    assert _reduced_trade_payload(notional_trade) == {
        "intent_type": "SECURITY_TRADE",
        "side": "BUY",
        "instrument_id": "NVDA",
        "notional": {"amount": "50", "currency": "USD"},
    }

    no_candidate_inputs = _inputs()
    assert (
        _largest_sellable_position(
            inputs=no_candidate_inputs,
            constraints=ProposalAlternativesConstraints(preserve_holdings=["AAPL", "SAP", "MSFT"]),
        )
        is None
    )
    synthetic_buy = _preferred_buy_instrument(
        inputs=AlternativeStrategyInputs(
            portfolio_id="pf_synthetic_buy",
            base_currency="USD",
            positions=(),
            cash_balances={},
            shelf_instruments=(StrategyShelfInstrument(instrument_id="NVDA", status="APPROVED"),),
            current_proposed_trades=(),
        ),
        constraints=ProposalAlternativesConstraints(),
        excluded_ids=set(),
        preferred_currency="USD",
    )
    assert synthetic_buy is not None
    assert synthetic_buy.instrument_id == "NVDA"
    assert synthetic_buy.quantity == Decimal("0")
