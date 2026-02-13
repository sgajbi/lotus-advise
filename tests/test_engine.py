import pytest
from decimal import Decimal
from src.core.models import (
    PortfolioSnapshot, MarketDataSnapshot, ModelPortfolio, ModelTarget,
    ShelfEntry, EngineOptions, Price, CashBalance, FxRate
)
from src.core.engine import run_simulation, get_fx_rate

@pytest.fixture
def base_portfolio():
    return PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))]
    )

@pytest.fixture
def base_options():
    return EngineOptions(suppress_dust_trades=True, fx_buffer_pct=Decimal("0.01"))

def test_missing_price_blocks_run(base_portfolio, base_options):
    """RFC Rule: Missing price for an eligible target must block the run."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[]) # Missing price
    
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    
    assert result.status == "BLOCKED"
    assert len(result.intents) == 0

def test_banned_instrument_is_excluded(base_portfolio, base_options):
    """RFC Rule: BANNED or SUSPENDED instruments are excluded from the universe."""
    model = ModelPortfolio(targets=[
        ModelTarget(instrument_id="EQ_GOOD", weight=Decimal("0.5")),
        ModelTarget(instrument_id="EQ_BANNED", weight=Decimal("0.5"))
    ])
    shelf = [
        ShelfEntry(instrument_id="EQ_GOOD", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_BANNED", status="BANNED")
    ]
    market_data = MarketDataSnapshot(prices=[
        Price(instrument_id="EQ_GOOD", price=Decimal("100.0"), currency="SGD"),
        Price(instrument_id="EQ_BANNED", price=Decimal("100.0"), currency="SGD")
    ])
    
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    
    assert result.status == "READY"
    assert len(result.intents) == 1
    assert result.intents[0].instrument_id == "EQ_GOOD"

def test_dust_trade_suppression(base_portfolio, base_options):
    """RFC Rule: Trades below min_notional are suppressed if options flag is True."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    
    # Target value is 10,000. Price is 100 -> Notional is 10,000. 
    # Min notional is 50,000. Trade should be suppressed.
    shelf = [ShelfEntry(
        instrument_id="EQ_1", 
        status="APPROVED", 
        min_notional={"amount": Decimal("50000.0"), "currency": "SGD"}
    )]
    market_data = MarketDataSnapshot(prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")])
    
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    
    assert result.status == "READY"
    assert len(result.intents) == 0 # Suppressed

def test_missing_fx_rate_raises_error(base_portfolio, base_options):
    """RFC Rule: Missing FX rates for cross-currency targets should raise an error/block."""
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("100.0"), currency="USD")],
        fx_rates=[] # Missing USD/SGD rate
    )
    
    with pytest.raises(ValueError, match="Missing FX rate for USD/SGD"):
        run_simulation(base_portfolio, market_data, model, shelf, base_options)

def test_zero_cash_zero_positions(base_options):
    """Edge Case: Empty portfolio should result in 0 trades, but READY status."""
    empty_portfolio = PortfolioSnapshot(portfolio_id="pf_empty", base_currency="SGD")
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")])
    
    result = run_simulation(empty_portfolio, market_data, model, shelf, base_options)
    
    assert result.status == "READY"
    assert len(result.intents) == 0
