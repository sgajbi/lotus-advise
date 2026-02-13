from decimal import Decimal

import pytest

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Price,
    ShelfEntry,
)


@pytest.fixture
def base_portfolio():
    return PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )


@pytest.fixture
def base_options():
    return EngineOptions(suppress_dust_trades=True, fx_buffer_pct=Decimal("0.01"))


def test_missing_price_blocks_run(base_portfolio, base_options):
    """RFC Rule: Missing price for an eligible target must block the run."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[])  # Missing price

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert len(result.intents) == 0


def test_banned_instrument_is_excluded(base_portfolio, base_options):
    """RFC Rule: BANNED or SUSPENDED instruments are excluded from the universe."""
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_GOOD", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_BANNED", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_GOOD", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_BANNED", status="BANNED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_GOOD", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_BANNED", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 1
    assert result.intents[0].instrument_id == "EQ_GOOD"


def test_dust_trade_suppression(base_portfolio, base_options):
    """RFC Rule: Trades below min_notional are suppressed if options flag is True."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])

    # Target value is 10,000. Price is 100 -> Notional is 10,000.
    # Min notional is 50,000. Trade should be suppressed.
    shelf = [
        ShelfEntry(
            instrument_id="EQ_1",
            status="APPROVED",
            min_notional={"amount": Decimal("50000.0"), "currency": "SGD"},
        )
    ]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 0  # Suppressed


def test_missing_fx_rate_raises_error(base_portfolio, base_options):
    """RFC Rule: Missing FX rates for cross-currency targets should raise an error/block."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("100.0"), currency="USD")],
        fx_rates=[],  # Missing USD/SGD rate
    )

    with pytest.raises(ValueError, match="Missing FX rate for USD/SGD"):
        run_simulation(base_portfolio, market_data, model, shelf, base_options)


def test_zero_cash_zero_positions(base_options):
    """Edge Case: Empty portfolio should result in 0 trades, but READY status."""
    empty_portfolio = PortfolioSnapshot(portfolio_id="pf_empty", base_currency="SGD")
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )

    result = run_simulation(empty_portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 0


def test_existing_position_valuation(base_options):
    """RFC Rule: Engine must correctly value existing positions and calculate delta for trades."""
    from src.core.models import Money, Position

    portfolio = PortfolioSnapshot(
        portfolio_id="pf_pos",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_1",
                quantity=Decimal("100"),
                market_value=Money(amount=Decimal("10000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    # Model wants 100% in EQ_1. Since we already have 10,000 SGD of EQ_1
    # (which is 100% of the portfolio),
    # the delta should be 0, resulting in NO trades.
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 0  # No trades needed, already at target


def test_infeasible_constraint_no_recipients(base_portfolio):
    """RFC Rule: If all assets breach cap and none can absorb excess, run is BLOCKED."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.5"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)
    assert result.status == "BLOCKED"


def test_infeasible_constraint_recursive_breach(base_portfolio):
    """RFC Rule: If redistribution causes another asset to breach cap, run is BLOCKED."""
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_1", weight=Decimal("0.6")),
            ModelTarget(instrument_id="EQ_2", weight=Decimal("0.4")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_1", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_2", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_2", price=Decimal("100.0"), currency="SGD"),
        ]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.45"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)
    assert result.status == "BLOCKED"


def test_sell_intent_generation(base_options):
    """RFC Rule: SELL intents are generated when target is below current, and sorted first."""
    from src.core.models import Money, Position

    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_1",
                quantity=Decimal("100"),
                market_value=Money(amount=Decimal("10000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    # Target wants 50% in EQ_1, 50% in EQ_2.
    # Current is 100% in EQ_1. Engine should SELL EQ_1, and BUY EQ_2.
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_1", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_2", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_1", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_2", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_2", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 2
    assert result.intents[0].action == "SELL"  # RFC Sorting Rule dictates SELL goes first
    assert result.intents[1].action == "BUY"


def test_sell_dust_trade_suppression(base_options):
    """RFC Rule: SELL intents below min_notional are suppressed."""
    from src.core.models import Money, Position

    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell_dust",
        base_currency="SGD",
        positions=[
            # We hold 10,000 SGD of EQ_1
            Position(
                instrument_id="EQ_1",
                quantity=Decimal("100"),
                market_value=Money(amount=Decimal("10000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    # Model wants 99% in EQ_1. Target = 9,900. Delta = -100.
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.99"))])
    # Min notional is 500. The sell of 100 should be suppressed.
    shelf = [
        ShelfEntry(
            instrument_id="EQ_1",
            status="APPROVED",
            min_notional={"amount": Decimal("500.0"), "currency": "SGD"},
        )
    ]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 0  # The sell was suppressed


def test_existing_foreign_cash_used_for_fx_deficit(base_options):
    """RFC Rule: Engine must use existing foreign cash before generating FX intents."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_foreign_cash",
        base_currency="SGD",
        positions=[],
        cash_balances=[
            CashBalance(currency="SGD", amount=Decimal("1000.0")),
            CashBalance(currency="USD", amount=Decimal("50.0")),  # <--- This hits line 131
        ],
    )
    # Total portfolio value = 1000 SGD + (50 USD * 1.0 FX) = 1050 SGD
    # Model wants 50% in US_EQ = 525 SGD target -> which is 525 USD
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("1.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.0"))],
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    fx_intents = [i for i in result.intents if i.intent_type == "FX"]
    assert len(fx_intents) == 1

    # We needed 525 USD. We had 50 USD. Deficit = 475 USD.
    # Buy amount with 1% buffer = 475 * 1.01 = 479.75 USD
    assert float(fx_intents[0].buy_amount.amount) == 479.75
