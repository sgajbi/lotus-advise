"""
FILE: tests/test_engine_safety.py
"""

from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
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
    # Model asks to SELL everything (weight 0)
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    return portfolio, market_data, model, shelf


def test_safety_no_shorting_block(base_options):
    """
    Simulate a scenario where logic (or data error) tries to sell more than held.
    We force this by manually injecting a starting position that is LOWER than what
    the engine *thinks* it is selling if we didn't check.
    Actually, to test the engine's guard, we can trick it by providing a Target
    that implies a sell, but then we modify the portfolio state 'under the hood'
    or just rely on the fact that the engine calculates sell qty based on 'Before' state.

    Wait, the engine calculates sell qty = (current_val - target_val) / price.
    If we have 100 units, and target 0, we sell 100.
    To trigger Over-Sell, we need to force the engine to generate a sell intent > 100.
    This is hard if the engine logic is correct!

    However, we can simulate a 'Data Race' or 'Bad Intent Generation' by mocking
    the intent generation or by creating a scenario where 'Current Market Value'
    is calculated high (high price), but 'Qty' is low.

    Let's try:
    Portfolio: 10 units. Price: 10. MV = 100.
    Target: 0.
    Intended Sell: 10 units.
    Safe.

    How to break it?
    If we have a negative cash balance that forces a liquidation?
    Or if we manually mock the intents in a lower-level test?

    Actually, let's test the 'Negative Holdings' guard by creating a starting portfolio
    that ALREADY has negative holdings (if allowed by schema but not by logic),
    or by using the 'Safety Block' demo logic where we might have a discrepancy.

    Better yet: Force a mismatch between 'Quantity' and 'Market Value' in input?
    If MV is huge, engine thinks we have lots to sell.
    Pos: 10 units. MV explicitly set to 1,000,000 (User error).
    Price: 1.
    Engine sees: Current Val 1,000,000. Target 0. Delta -1,000,000.
    Qty to sell: 1,000,000 / 1 = 1,000,000 units.
    Held: 10 units.
    Result: Sell 1,000,000. New Qty: -999,990. -> BLOCKED.
    """
    portfolio, market_data, model, shelf = get_base_data()

    # Poison the input: High Market Value, Low Quantity
    portfolio.positions[0].quantity = Decimal("10")
    # MV implies we have 1000 units (at px 10)
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    # Check for specific Rule Failure
    rule = next((r for r in result.rule_results if r.rule_id == "NO_SHORTING"), None)
    assert rule is not None
    assert rule.status == "FAIL"
    assert rule.reason_code == "SELL_EXCEEDS_HOLDINGS"


def test_safety_insufficient_cash_block(base_options):
    """
    Test that running out of cash blocks the sim.
    Scenario: Buying a new asset with target weight > cash available.
    """
    portfolio, market_data, model, shelf = get_base_data()

    # Start with very little cash
    portfolio.cash_balances[0].amount = Decimal("10.0")
    # Existing asset is 100 units * 10 = 1000. Total = 1010.

    # Add a new asset to buy
    market_data.prices.append(
        Price(instrument_id="NEW_ASSET", price=Decimal("100.0"), currency="SGD")
    )
    shelf.append(ShelfEntry(instrument_id="NEW_ASSET", status="APPROVED"))

    # Target: 50% NEW_ASSET (~505 SGD), 50% EQ_1 (~505 SGD)
    # To buy 505 SGD of NEW_ASSET, we need 505 cash. We have 10.
    # We must sell EQ_1 first.
    # Current EQ_1 = 1000. Target = 505. Sell 495.
    # Cash proceeds = 495 + 10 = 505.
    # Buy NEW_ASSET = 505.
    # This SHOULD pass if netting works.

    # To fail, we need to buy WITHOUT selling, or buy MORE than sell proceeds.
    # Let's target 100% NEW_ASSET (1010 SGD).
    # Sell EQ_1 (1000) -> Cash 1010. Buy NEW_ASSET (1000). Passes.

    # To fail: Price moves against us? Or huge fee buffer?
    # Or simply: Total Model Weight > 100%? (Engine normalizes this usually).
    #
    # Let's try: Buy intention generated, but no cash.
    # Case: Don't sell EQ_1 (Lock it), but try to buy NEW_ASSET.
    # EQ_1 is not in model targets -> Locked? No, if not in targets, it's sold to 0 unless locked.
    # Let's use 'Locking' via exclusion?

    # Simpler: Target NEW_ASSET 100%.
    # But shelf for EQ_1 is RESTRICTED (Can't sell?).
    # If can't sell EQ_1, we hold 1000.
    # But Model wants 100% NEW_ASSET.
    # Engine calculates targets...

    # Let's just FORCE a cash overdraft by defining a model that the engine *tries* to execute.
    #
    # Setup:
    # Cash: 0.
    # Pos: EQ_1 (1000 val). Locked (Restricted).
    # Model: EQ_2 (Target 50%).
    # Engine normalization might scale EQ_2 down if EQ_1 is locked.
    #
    # Let's use the 'Cash Buffer' failure mode or FX failure.
    #
    # Let's try FX Funding failure.
    # Cash SGD: 0.
    # Buy USD Asset.
    # No SGD to sell.
    # FX Gen: Sell SGD / Buy USD.
    # SGD goes negative.

    portfolio.cash_balances[0].amount = Decimal("0.0")
    portfolio.positions = []  # No assets to sell.
    market_data.prices = [Price(instrument_id="US_EQ", price=Decimal("100.0"), currency="USD")]
    market_data.fx_rates = [FxRate(pair="USD/SGD", rate=Decimal("1.3"))]
    model.targets = [ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))]  # 100% US
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]

    # Total Value = 0.
    # Target Value = 0.
    # Result: No trades.

    # We need POSITIVE value but Illiquid.
    portfolio.positions = [
        Position(instrument_id="LOCKED_ASSET", quantity=Decimal("10"))
    ]  # Val = 1000 SGD.
    market_data.prices.append(
        Price(instrument_id="LOCKED_ASSET", price=Decimal("100.0"), currency="SGD")
    )
    # LOCKED_ASSET not in shelf -> Locked.
    # Total Val = 1000.
    # Model: US_EQ 100%.
    # Engine: LOCKED_ASSET is locked (100%). US_EQ (0%).
    # Result: No trade.

    # Okay, the engine is too smart. It prevents generation of bad targets.
    # We need to trick the SIMULATOR, not the Target Gen.
    #
    # Trick: FX Rate change between Target Gen and Simulation?
    # No, same snapshot.
    #
    # Trick: Dust threshold?
    #
    # Let's relying on 'options.min_cash_buffer_pct' being negative? No.
    #
    # How about: We have 100 SGD.
    # We buy 100 SGD of EQ.
    # But we have a pending buy or something?
    #
    # Actually, the 'INSUFFICIENT_CASH' rule is mostly for cases where
    # FX friction or slight miscalculation causes a dip below zero.
    # Let's force it by manually creating an intent that spends too much?
    # No, we simulate full engine.

    # Let's use the FX spread.
    # We have 100 SGD.
    # We buy USD asset worth 100 SGD.
    # To buy USD, we sell SGD.
    # If there is a bid/ask spread or buffer...
    # option 'fx_buffer_pct' defaults to 0.01 (1%).
    # We need 100 SGD equivalent of USD.
    # Engine sees we need X USD.
    # FX Trade: Buy X USD. Sell (X * Rate * 1.01) SGD.
    # Cost = 101 SGD.
    # We have 100 SGD.
    # Result: -1 SGD Balance. -> BLOCKED.

    portfolio.cash_balances[0].amount = Decimal("100.0")
    market_data.prices = [Price(instrument_id="US_EQ", price=Decimal("10.0"), currency="USD")]
    # FX Rate 1.0.
    market_data.fx_rates = [FxRate(pair="USD/SGD", rate=Decimal("1.0"))]
    model.targets = [ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))]
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]

    # Ensure fx buffer is ON
    base_options.fx_buffer_pct = Decimal("0.05")  # 5% buffer

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    rule = next((r for r in result.rule_results if r.rule_id == "INSUFFICIENT_CASH"), None)
    assert rule is not None
    assert rule.status == "FAIL"


def test_reconciliation_object_populated_on_success(base_options):
    """Verify reconciliation object is present and OK for valid runs."""
    portfolio, market_data, model, shelf = get_base_data()
    # Simple valid drift
    model.targets[0].weight = Decimal("0.5")  # Sell half

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert result.reconciliation is not None
    assert result.reconciliation.status == "OK"
    assert abs(result.reconciliation.delta.amount) < Decimal("1.0")
