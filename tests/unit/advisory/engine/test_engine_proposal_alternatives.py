import pytest

from src.core.advisory import (
    AlternativesRequestNormalizationError,
    AlternativeStrategyInputs,
    ProposalAlternativesRequest,
    build_candidate_seeds,
    normalize_alternatives_request,
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

    inputs = AlternativeStrategyInputs(
        portfolio_id="pf_demo",
        base_currency="USD",
        held_instrument_ids=("AAPL", "MSFT"),
        shelf_instrument_ids=("AAPL", "MSFT", "USD"),
        current_trade_instrument_ids=("MSFT",),
    )

    first = build_candidate_seeds(request=normalized, inputs=inputs)
    second = build_candidate_seeds(request=normalized, inputs=inputs)

    assert [seed.objective for seed in first] == [
        "LOWER_TURNOVER",
        "REDUCE_CONCENTRATION",
        "IMPROVE_CURRENCY_ALIGNMENT",
    ]
    assert [seed.candidate_id for seed in first] == [seed.candidate_id for seed in second]
    assert first[0].metadata["pivot_instrument_id"] == "MSFT"
    assert first[1].strategy_id == "reduce_concentration_v1"


def test_build_candidate_seeds_requires_no_upstream_call_context_beyond_inputs():
    normalized = normalize_alternatives_request(
        ProposalAlternativesRequest(objectives=["RAISE_CASH"])
    )
    assert normalized is not None

    seeds = build_candidate_seeds(
        request=normalized,
        inputs=AlternativeStrategyInputs(
            portfolio_id="pf_cash",
            base_currency="USD",
            held_instrument_ids=("AAPL",),
        ),
    )

    assert len(seeds) == 1
    assert seeds[0].generated_intents == []
    assert seeds[0].metadata["portfolio_id"] == "pf_cash"
