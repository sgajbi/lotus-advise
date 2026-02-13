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
    Money,
    PortfolioSnapshot,
    Position,
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
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[])
    with pytest.raises(ValueError, match="Missing price"):
        run_simulation(base_portfolio, market_data, model, shelf, base_options)


def test_missing_shelf_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_SHELF", weight=Decimal("1.0"))]
    )
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_NO_SHELF", price=Decimal("10.0"), currency="SGD")]
    )
    with pytest.raises(ValueError, match="Missing shelf entry"):
        run_simulation(base_portfolio, market_data, model, shelf, base_options)


def test_restricted_asset_exclusion(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_RESTRICTED", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_RESTRICTED", status="RESTRICTED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_RESTRICTED", price=Decimal("10.0"), currency="SGD")]
    )
    base_options.allow_restricted = False
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert len(result.universe.excluded) == 1
    assert result.universe.excluded[0].reason_code == "SHELF_STATUS_RESTRICTED"


def test_banned_instrument_is_excluded(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_BANNED", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_BANNED", status="BANNED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_BANNED", price=Decimal("100.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.universe.excluded[0].instrument_id == "EQ_BANNED"


def test_dust_trade_suppression(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
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
    assert len(result.intents) == 0
    # Because trades are suppressed, 100% cash remains, breaking soft rule
    assert result.status == "PENDING_REVIEW"


def test_sell_dust_trade_suppression(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell_dust",
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
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.99"))])
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
    assert len(result.intents) == 0
    # Cash remains 0%, so it passes the soft rule
    assert result.status == "READY"


def test_infeasible_constraint_no_recipients(base_portfolio):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.5"))
    with pytest.raises(ValueError, match="CONSTRAINT_INFEASIBLE"):
        run_simulation(base_portfolio, market_data, model, shelf, opts)


def test_infeasible_constraint_secondary_breach(base_portfolio):
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
    with pytest.raises(ValueError, match="secondary breach"):
        run_simulation(base_portfolio, market_data, model, shelf, opts)


def test_sell_intent_generation(base_options):
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
    assert result.intents[0].side == "SELL"
    assert result.intents[1].side == "BUY"


def test_existing_foreign_cash_used_for_fx_deficit(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_foreign_cash",
        base_currency="SGD",
        positions=[],
        cash_balances=[
            CashBalance(currency="SGD", amount=Decimal("1000.0")),
            CashBalance(currency="USD", amount=Decimal("50.0")),
        ],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("1.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.0"))],
    )
    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    fx_intents = [i for i in result.intents if i.intent_type == "FX_SPOT"]
    assert float(fx_intents[0].buy_amount) == 479.75

    portfolio = PortfolioSnapshot(
        portfolio_id="pf_bad_pos",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_BAD", quantity=Decimal("100"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("10.0"), currency="SGD")]
    )
    with pytest.raises(ValueError, match="Missing price and market_value"):
        run_simulation(portfolio, market_data, model, shelf, base_options)


def test_missing_shelf_non_blocking(base_portfolio, base_options):
    base_options.block_on_missing_prices = False
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_SHELF", weight=Decimal("1.0"))]
    )
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_NO_SHELF", price=Decimal("10.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    # 0 trades generated, meaning 100% cash remains, breaking 5% soft rule
    assert result.status == "PENDING_REVIEW"
    assert len(result.intents) == 0


def test_missing_price_non_blocking(base_portfolio, base_options):
    base_options.block_on_missing_prices = False
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_PRICE", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_NO_PRICE", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[])
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    # 0 trades generated, meaning 100% cash remains, breaking 5% soft rule
    assert result.status == "PENDING_REVIEW"
    assert len(result.intents) == 0


def test_position_derived_valuation(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_deriv",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_1", quantity=Decimal("100"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("10.0"), currency="SGD")]
    )
    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    assert result.status == "READY"


def test_after_state_simulation_updates_cash(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sim",
        base_currency="SGD",
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 1

    sim_cash = next(c for c in result.after_simulated.cash_balances if c.currency == "SGD")
    assert sim_cash.amount == Decimal("0.0")


def test_rule_engine_soft_fail_escalates_status(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_soft",
        base_currency="SGD",
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "PENDING_REVIEW"
    rule_res = next(r for r in result.rule_results if r.rule_id == "CASH_BAND")
    assert rule_res.status == "FAIL"
    assert rule_res.severity == "SOFT"
    assert rule_res.measured == Decimal("0.5")


def test_sell_only_blocks_buys_and_redistributes(base_options):
    """If an asset is SELL_ONLY, its target is set to 0 and excess is redistributed."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell_only",
        base_currency="SGD",
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    # Model wants 50% in an Approved asset, and 50% in a Sell-Only asset.
    # The engine should cap the Sell-Only at 0%, and redistribute the 50% to the Approved asset.
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_APPROVED", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_SELL_ONLY", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_APPROVED", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_SELL_ONLY", status="SELL_ONLY"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_APPROVED", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_SELL_ONLY", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Expecting 1 intent: A buy of 100 shares of EQ_APPROVED (using the full 100% / 10,000 SGD)
    assert len(result.intents) == 1
    assert result.intents[0].instrument_id == "EQ_APPROVED"
    assert result.intents[0].quantity == Decimal("100")

    # Verify the universe classifications
    assert "EQ_APPROVED" in result.universe.eligible_for_buy
    assert "EQ_SELL_ONLY" not in result.universe.eligible_for_buy
    assert "EQ_SELL_ONLY" in result.universe.eligible_for_sell

    # Verify the exclusion reason is tracked
    exclusion = next(e for e in result.universe.excluded if e.instrument_id == "EQ_SELL_ONLY")
    assert exclusion.reason_code == "SHELF_STATUS_SELL_ONLY_BUY_BLOCKED"


def test_sell_only_allows_liquidation(base_options):
    """If an asset is SELL_ONLY and we hold it, the engine should generate a SELL intent."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_liq",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_SELL_ONLY", quantity=Decimal("100"))],
    )
    # Model doesn't want it (Target = 0 implicitly, or 50% explicitly which gets zeroed out)
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_APPROVED", weight=Decimal("1.0")),
            ModelTarget(instrument_id="EQ_SELL_ONLY", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_APPROVED", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_SELL_ONLY", status="SELL_ONLY"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_APPROVED", price=Decimal("10.0"), currency="SGD"),
            Price(instrument_id="EQ_SELL_ONLY", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # We should see a SELL for the SELL_ONLY asset, and a BUY for the APPROVED asset.
    assert len(result.intents) == 2
    assert result.intents[0].side == "SELL"
    assert result.intents[0].instrument_id == "EQ_SELL_ONLY"


def test_all_assets_sell_only_blocks_run(base_portfolio, base_options):
    """Hits line 131: Fails if all assets in model are SELL_ONLY (no redistribution)."""
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_SELL_ONLY", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_SELL_ONLY", status="SELL_ONLY")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_SELL_ONLY", price=Decimal("10.0"), currency="SGD")]
    )

    with pytest.raises(ValueError, match="All assets are SELL_ONLY or excluded"):
        run_simulation(base_portfolio, market_data, model, shelf, base_options)

    """Hits line 34: Ensure ValueError is raised when both price and MV are missing."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_bad_pos",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_BAD", quantity=Decimal("100"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_BAD", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_BAD", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[])

    with pytest.raises(
        ValueError, match="Cannot value position EQ_BAD: Missing price and market_value"
    ):
        run_simulation(portfolio, market_data, model, shelf, base_options)
