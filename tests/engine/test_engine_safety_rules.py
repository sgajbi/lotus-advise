from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
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


def get_base_data():
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_safe",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_1", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("10.0"), currency="SGD")], fx_rates=[]
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    return portfolio, market_data, model, shelf


def test_safety_no_shorting_block(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    portfolio.positions[0].quantity = Decimal("10")
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    rule = next((r for r in result.rule_results if r.rule_id == "NO_SHORTING"), None)
    assert rule is not None
    assert rule.status == "FAIL"
    assert rule.reason_code == "SELL_EXCEEDS_HOLDINGS"


def test_safety_insufficient_cash_block(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    portfolio.positions = []
    portfolio.cash_balances[0].amount = Decimal("100.0")

    market_data.prices = [Price(instrument_id="US_EQ", price=Decimal("10.0"), currency="USD")]
    market_data.fx_rates = [FxRate(pair="USD/SGD", rate=Decimal("1.0"))]
    model.targets = [ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))]
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    options = base_options.model_copy(update={"fx_buffer_pct": Decimal("0.05")})

    result = run_simulation(portfolio, market_data, model, shelf, options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    rule = next((r for r in result.rule_results if r.rule_id == "INSUFFICIENT_CASH"), None)
    assert rule is not None
    assert rule.status == "FAIL"


def test_reconciliation_object_populated_on_success(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    model.targets[0].weight = Decimal("0.5")

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status in ["READY", "PENDING_REVIEW"]
    assert result.reconciliation is not None
    assert result.reconciliation.status == "OK"
    assert abs(result.reconciliation.delta.amount) < Decimal("1.0")
