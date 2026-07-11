import pytest

from src.integrations.lotus_core.stateful_context_market_data import (
    InvalidLotusCoreFxRateError,
    build_prices,
    derive_fx_rates,
)


def test_build_prices_skips_cash_missing_values_and_deduplicates_by_instrument() -> None:
    prices = build_prices(
        {
            "positions": [
                {
                    "security_id": "SEC_A",
                    "currency": "USD",
                    "asset_class": "EQUITY",
                    "valuation": {"market_price": "100.25"},
                },
                {
                    "security_id": "SEC_A",
                    "currency": "USD",
                    "asset_class": "EQUITY",
                    "valuation": {"market_price": "101.50"},
                },
                {
                    "security_id": "CASH_USD",
                    "currency": "USD",
                    "asset_class": "CASH",
                    "valuation": {"market_price": "1"},
                },
                {
                    "security_id": "SEC_MISSING_PRICE",
                    "currency": "USD",
                    "asset_class": "EQUITY",
                    "valuation": {},
                },
                {
                    "security_id": "SEC_MISSING_VALUATION",
                    "currency": "USD",
                    "asset_class": "EQUITY",
                },
            ]
        }
    )

    assert [price.model_dump(mode="json") for price in prices] == [
        {"instrument_id": "SEC_A", "price": "101.50", "currency": "USD"}
    ]


def test_derive_fx_rates_uses_position_and_cash_values_with_last_pair_winning() -> None:
    fx_rates = derive_fx_rates(
        portfolio_base_currency="USD",
        positions_payload={
            "positions": [
                {
                    "security_id": "SEC_CH",
                    "currency": "CHF",
                    "valuation": {
                        "market_value": "110",
                        "market_value_local": "100",
                    },
                },
                {
                    "security_id": "SEC_EU",
                    "currency": "EUR",
                    "valuation": {
                        "market_value": "132",
                        "market_value_local": "120",
                    },
                },
            ]
        },
        cash_payload={
            "cash_accounts": [
                {
                    "account_currency": "CHF",
                    "balance_portfolio_currency": "111",
                    "balance_account_currency": "100",
                },
                {
                    "account_currency": "USD",
                    "balance_portfolio_currency": "25",
                    "balance_account_currency": "25",
                },
            ]
        },
    )

    assert [rate.model_dump(mode="json") for rate in fx_rates] == [
        {"pair": "CHF/USD", "rate": "1.11"},
        {"pair": "EUR/USD", "rate": "1.1"},
    ]


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [
        ("90", "0"),
        ("bad-rate", "100"),
        ("NaN", "100"),
        ("-90", "100"),
    ],
)
def test_derive_fx_rates_rejects_invalid_explicit_source_fx_values(
    numerator: str, denominator: str
) -> None:
    with pytest.raises(InvalidLotusCoreFxRateError, match="LOTUS_CORE_STATEFUL_FX_INVALID"):
        derive_fx_rates(
            portfolio_base_currency="USD",
            positions_payload={
                "positions": [
                    {
                        "security_id": "SEC_INVALID",
                        "currency": "GBP",
                        "valuation": {
                            "market_value": numerator,
                            "market_value_local": denominator,
                        },
                    }
                ]
            },
            cash_payload={"cash_accounts": []},
        )
