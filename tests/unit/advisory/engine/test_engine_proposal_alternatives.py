from decimal import Decimal

import pytest

from src.core.advisory import (
    AlternativesRequestNormalizationError,
    AlternativeStrategyInputs,
    ProposalAlternativesRequest,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
    build_candidate_plan,
    build_candidate_seeds,
    normalize_alternatives_request,
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
