"""
FILE: tests/dependencies/test_dependency_chains.py
"""

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
)
from tests.assertions import fx_intents, security_intents
from tests.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def test_dependency_chain_generation():
    """
    Scenario: Buy DBS (SGD) using USD Base.
    Expect: FX Buy SGD (dependent on nothing) -> Buy DBS (dependent on FX).
    """
    portfolio = portfolio_snapshot(
        portfolio_id="pf_dep_1",
        base_currency="USD",
        cash_balances=[cash("USD", "100000")],
    )
    market_data = market_data_snapshot(
        prices=[price("DBS", "30.00", "SGD")],
        fx_rates=[fx("USD/SGD", "1.35")],
    )
    model = model_portfolio(targets=[target("DBS", "0.5")])
    shelf = [shelf_entry("DBS", status="APPROVED")]

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    fx_i = fx_intents(result)
    sec_i = security_intents(result)

    assert len(fx_i) == 1
    assert len(sec_i) == 1

    fx_intent = fx_i[0]
    sec = sec_i[0]

    assert fx_intent.buy_currency == "SGD"
    assert sec.instrument_id == "DBS"

    assert fx_intent.intent_id in sec.dependencies


def test_dependency_multi_leg_chain():
    """
    Complex: Sell EUR -> SGD -> Buy USD.
    """
    portfolio = portfolio_snapshot(
        portfolio_id="pf_chain",
        base_currency="SGD",
        positions=[
            position("EUR_ASSET", "10"),
        ],
        cash_balances=[cash("SGD", "0.0")],
    )

    model = model_portfolio(targets=[target("EUR_ASSET", "0.0"), target("USD_ASSET", "1.0")])

    shelf = [
        shelf_entry("EUR_ASSET", status="APPROVED"),
        shelf_entry("USD_ASSET", status="APPROVED"),
    ]

    market_data = market_data_snapshot(
        prices=[
            price("EUR_ASSET", "100.0", "EUR"),
            price("USD_ASSET", "100.0", "USD"),
        ],
        fx_rates=[
            fx("EUR/SGD", "1.5"),
            fx("USD/SGD", "1.3"),
        ],
    )

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    sec_i = security_intents(result)
    fx_i = fx_intents(result)

    buy_sec = next(i for i in sec_i if i.instrument_id == "USD_ASSET")

    fx_buy_usd = next(i for i in fx_i if i.buy_currency == "USD")

    assert fx_buy_usd.intent_id in buy_sec.dependencies
