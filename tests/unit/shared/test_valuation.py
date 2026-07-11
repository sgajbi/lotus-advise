from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.engine_options_models import EngineOptions, ValuationMode
from src.core.portfolio_models import (
    CashBalance,
    FxRate,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)
from src.core.valuation import ValuationService, build_simulated_state, get_fx_rate


def test_get_fx_rate_returns_one_for_matching_currencies() -> None:
    rate = get_fx_rate(MarketDataSnapshot(prices=[], fx_rates=[]), "USD", "USD")

    assert rate == Decimal("1.0")


def test_get_fx_rate_uses_direct_market_pair() -> None:
    rate = get_fx_rate(
        MarketDataSnapshot(
            prices=[],
            fx_rates=[FxRate(pair="EUR/USD", rate="1.25")],
        ),
        "EUR",
        "USD",
    )

    assert rate == Decimal("1.25")


def test_get_fx_rate_uses_inverse_market_pair() -> None:
    rate = get_fx_rate(
        MarketDataSnapshot(
            prices=[],
            fx_rates=[FxRate(pair="USD/EUR", rate="0.8")],
        ),
        "EUR",
        "USD",
    )

    assert rate == Decimal("1.25")


def test_get_fx_rate_returns_none_when_pair_is_missing() -> None:
    rate = get_fx_rate(MarketDataSnapshot(prices=[], fx_rates=[]), "EUR", "USD")

    assert rate is None


@pytest.mark.parametrize("rate", ["0", "-1", "NaN", "Infinity", "-Infinity", "bad"])
def test_fx_rate_rejects_invalid_values_before_valuation(rate: str) -> None:
    with pytest.raises(ValidationError):
        MarketDataSnapshot(
            prices=[],
            fx_rates=[{"pair": "EUR/USD", "rate": rate}],
        )


def test_value_position_uses_mark_to_market_fx_conversion() -> None:
    summary = ValuationService.value_position(
        Position(instrument_id="EQ_EU", quantity="3"),
        MarketDataSnapshot(
            prices=[Price(instrument_id="EQ_EU", price="20", currency="EUR")],
            fx_rates=[FxRate(pair="EUR/USD", rate="1.5")],
        ),
        "USD",
        EngineOptions(),
        dq_log={},
    )

    assert summary.price == Money(amount=Decimal("20"), currency="EUR")
    assert summary.value_in_instrument_ccy == Money(amount=Decimal("60"), currency="EUR")
    assert summary.value_in_base_ccy == Money(amount=Decimal("90.0"), currency="USD")


def test_value_position_preserves_trusted_base_authority_for_foreign_price() -> None:
    summary = ValuationService.value_position(
        Position(
            instrument_id="EQ_EU",
            quantity="3",
            market_value=Money(amount="95", currency="USD"),
        ),
        MarketDataSnapshot(
            prices=[Price(instrument_id="EQ_EU", price="20", currency="EUR")],
            fx_rates=[FxRate(pair="EUR/USD", rate="1.5")],
        ),
        "USD",
        EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT),
        dq_log={},
    )

    assert summary.price == Money(amount=Decimal("20"), currency="EUR")
    assert summary.value_in_instrument_ccy == Money(amount=Decimal("60"), currency="EUR")
    assert summary.value_in_base_ccy == Money(amount=Decimal("95"), currency="USD")


def test_build_simulated_state_values_positions_cash_and_allocations() -> None:
    dq_log: dict[str, list[str]] = {}
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_1",
        base_currency="USD",
        positions=[
            Position(instrument_id="EQ_US", quantity="2"),
            Position(instrument_id="EQ_EU", quantity="1"),
        ],
        cash_balances=[
            CashBalance(currency="USD", amount="100"),
            CashBalance(currency="EUR", amount="25"),
        ],
    )
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_US", price="100", currency="USD"),
            Price(instrument_id="EQ_EU", price="50", currency="EUR"),
        ],
        fx_rates=[FxRate(pair="EUR/USD", rate="2")],
    )
    shelf = [
        ShelfEntry(
            instrument_id="EQ_US",
            status="APPROVED",
            asset_class="Equity",
            attributes={"sector": "Technology", "region": "US"},
        ),
        ShelfEntry(
            instrument_id="EQ_EU",
            status="APPROVED",
            asset_class="Equity",
            attributes={"sector": "Technology", "region": "Europe"},
        ),
    ]

    state = build_simulated_state(portfolio, market_data, shelf, dq_log, warnings=[])

    assert state.total_value.amount == Decimal("450")
    assert [position.weight for position in state.positions] == [
        Decimal("0.4444444444444444444444444444"),
        Decimal("0.2222222222222222222222222222"),
    ]
    assert _allocation_value(state.allocation_by_asset_class, "Equity") == Decimal("300")
    assert _allocation_value(state.allocation_by_asset_class, "CASH") == Decimal("150")
    assert _allocation_value(state.allocation_by_attribute["sector"], "Technology") == Decimal(
        "300"
    )
    assert _allocation_value(state.allocation_by_attribute["region"], "US") == Decimal("200")
    assert _allocation_value(state.allocation_by_attribute["region"], "Europe") == Decimal("100")
    assert dq_log == {}


def test_build_simulated_state_uses_inverse_fx_pair_for_multi_currency_inputs() -> None:
    dq_log: dict[str, list[str]] = {}
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_1",
        base_currency="USD",
        positions=[Position(instrument_id="EQ_EU", quantity="1")],
        cash_balances=[CashBalance(currency="EUR", amount="25")],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_EU", price="50", currency="EUR")],
        fx_rates=[FxRate(pair="USD/EUR", rate="0.5")],
    )

    state = build_simulated_state(portfolio, market_data, [], dq_log, warnings=[])

    assert get_fx_rate(market_data, "EUR", "USD") == Decimal("2")
    assert state.total_value.amount == Decimal("150")
    assert state.positions[0].value_in_base_ccy == Money(amount=Decimal("100"), currency="USD")
    assert _allocation_value(state.allocation_by_asset_class, "CASH") == Decimal("50")
    assert dq_log == {}


def test_build_simulated_state_records_missing_price_and_fx_once_per_cash_balance() -> None:
    dq_log: dict[str, list[str]] = {}
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_1",
        base_currency="USD",
        positions=[Position(instrument_id="EQ_MISSING", quantity="3")],
        cash_balances=[CashBalance(currency="EUR", amount="25")],
    )
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])

    state = build_simulated_state(portfolio, market_data, [], dq_log, warnings=[])

    assert state.total_value.amount == Decimal("0")
    assert _allocation_value(state.allocation_by_asset_class, "UNKNOWN") == Decimal("0")
    assert _allocation_value(state.allocation_by_asset_class, "CASH") == Decimal("0")
    assert dq_log["price_missing"] == ["EQ_MISSING"]
    assert dq_log["fx_missing"] == ["EUR/USD"]


def _allocation_value(allocations, key: str) -> Decimal:
    return next(allocation.value.amount for allocation in allocations if allocation.key == key)
