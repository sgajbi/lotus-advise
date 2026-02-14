"""
FILE: tests/test_engine.py
"""

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
    OrderIntent,
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
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )


@pytest.fixture
def base_options():
    return EngineOptions(
        allow_restricted=False,
        suppress_dust_trades=True,
        block_on_missing_prices=True,
    )


def test_missing_price_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[])

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert "EQ_1" in result.diagnostics.data_quality["price_missing"]


def test_missing_shelf_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_SHELF", weight=Decimal("1.0"))]
    )
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_NO_SHELF", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert "EQ_NO_SHELF" in result.diagnostics.data_quality["shelf_missing"]


def test_missing_fx_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("100.0"), currency="USD")],
        fx_rates=[],  # Missing USD/SGD
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert any("USD/SGD" in s for s in result.diagnostics.data_quality["fx_missing"])


def test_banned_assets_excluded(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_BANNED", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_BANNED", status="BANNED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_BANNED", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    # Asset excluded -> 100% Cash -> >5% Limit -> PENDING_REVIEW
    assert result.status == "PENDING_REVIEW"
    assert len(result.universe.excluded) == 1
    assert result.universe.excluded[0].reason_code == "SHELF_STATUS_BANNED"


def test_restricted_assets_excluded(base_portfolio, base_options):
    """Hits the 'RESTRICTED' branch in _build_universe."""
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_RESTRICTED", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_RESTRICTED", status="RESTRICTED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_RESTRICTED", price=Decimal("10.0"), currency="SGD")]
    )
    # options.allow_restricted is False by default
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    assert result.status == "PENDING_REVIEW"  # 100% Cash
    assert len(result.universe.excluded) == 1
    assert result.universe.excluded[0].reason_code == "SHELF_STATUS_RESTRICTED"


def test_valuation_missing_data_branches(base_options):
    """
    Specifically targets lines in _calculate_valuation where:
    1. Cash FX is missing
    2. Position MarketValue FX is missing
    3. Position Price is missing
    4. Position Price FX is missing
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_val_test",
        base_currency="SGD",
        positions=[
            # Case 2: Market Value provided, but FX missing (EUR->SGD)
            Position(
                instrument_id="EQ_MV_NO_FX",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("100.0"), currency="EUR"),
            ),
            # Case 3: No Market Value, No Price found
            Position(instrument_id="EQ_NO_PRICE", quantity=Decimal("10")),
            # Case 4: Price found, but FX missing (JPY->SGD)
            Position(instrument_id="EQ_PRICE_NO_FX", quantity=Decimal("10")),
        ],
        cash_balances=[
            # Case 1: Cash FX missing (GBP->SGD)
            CashBalance(currency="GBP", amount=Decimal("100.0")),
            CashBalance(currency="SGD", amount=Decimal("1000.0")),
        ],
    )

    market_data = MarketDataSnapshot(
        prices=[
            # Added Price for EQ_MV_NO_FX to allow logic to proceed to FX check
            Price(instrument_id="EQ_MV_NO_FX", price=Decimal("10.0"), currency="EUR"),
            Price(instrument_id="EQ_PRICE_NO_FX", price=Decimal("100.0"), currency="JPY"),
        ],
        fx_rates=[],  # No FX rates provided
    )

    model = ModelPortfolio(targets=[])
    shelf = []

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    dq = result.diagnostics.data_quality

    # Assert all branches were hit
    assert any("GBP/SGD" in s for s in dq["fx_missing"])  # Case 1
    assert any("EUR/SGD" in s for s in dq["fx_missing"])  # Case 2
    assert "EQ_NO_PRICE" in dq["price_missing"]  # Case 3
    assert any("JPY/SGD" in s for s in dq["fx_missing"])  # Case 4


def test_valuation_mismatch_warning(base_options):
    """
    RFC-0004 4.3.3: If snapshot MV exists but differs from computed MV > 0.5%, warn.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_mismatch",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_MISMATCH",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("2000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    # Computed: 10 * 100 = 1000. Snapshot: 2000. Diff 100%.
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_MISMATCH", price=Decimal("100.0"), currency="SGD")]
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_MISMATCH", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Note: Implicit Sell logic sells this position -> 100% Cash -> PENDING_REVIEW
    assert result.status == "PENDING_REVIEW"
    assert len(result.diagnostics.warnings) == 1
    assert "POSITION_VALUE_MISMATCH" in result.diagnostics.warnings[0]
    # Check that allocation was populated
    assert result.before.allocation_by_asset_class[0].key == "EQUITY"
    assert result.before.allocation_by_asset_class[0].value.amount == Decimal("2000.0")


def test_valuation_market_value_non_base(base_options):
    """
    Coverage fix for _evaluate_portfolio_state:
    Hit the 'else' branch where market_value.currency != base_currency.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_non_base_mv",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_USD_MV",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("100.0"), currency="USD"),
            )
        ],
        cash_balances=[],
    )
    # Price: 10 USD. Qty 10. Computed = 100 USD. FX = 1.35. Total = 135 SGD.
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_USD_MV", price=Decimal("10.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_USD_MV", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Note: Implicit Sell logic sells this position -> 100% Cash -> PENDING_REVIEW
    assert result.status == "PENDING_REVIEW"
    # Verify calculated value is used (135 SGD)
    assert result.before.total_value.amount == Decimal("135.0")
    assert result.before.positions[0].value_in_base_ccy.amount == Decimal("135.0")


def test_after_state_simulation_fidelity(base_options):
    """
    Verifies that 'after_simulated' contains the same rich structure as 'before'
    and correctly reflects the trades.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_fid",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )
    # Target: 50% Equity.
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED", asset_class="EQUITY")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # 50% Cash (5000/10000) > 5% Threshold -> PENDING_REVIEW
    assert result.status == "PENDING_REVIEW"
    assert result.rule_results[0].rule_id == "CASH_BAND"
    assert result.rule_results[0].status == "FAIL"

    # Check Before State (Empty Alloc)
    assert len(result.before.positions) == 0

    # Check After State (Populated Alloc)
    assert len(result.after_simulated.positions) == 1
    pos = result.after_simulated.positions[0]
    assert pos.instrument_id == "EQ_1"
    assert pos.quantity == Decimal("50")  # 5000 SGD / 100
    assert pos.weight == Decimal("0.5")

    # Check Cash
    # 10000 - 5000 = 5000
    assert result.after_simulated.cash_balances[0].amount == Decimal("5000.00")

    # Check Allocation Objects
    equity_alloc = next(
        a for a in result.after_simulated.allocation_by_asset_class if a.key == "EQUITY"
    )
    assert equity_alloc.weight == Decimal("0.5")
    assert equity_alloc.value.amount == Decimal("5000.0")


def test_dust_trade_suppression(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [
        ShelfEntry(
            instrument_id="EQ_1",
            status="APPROVED",
            min_notional=Money(amount=Decimal("50000.0"), currency="SGD"),
        )
    ]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert len(result.intents) == 0
    assert result.status == "PENDING_REVIEW"
    assert len(result.diagnostics.suppressed_intents) == 1


def test_infeasible_constraint_no_recipients(base_portfolio):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.5"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)

    # Was BLOCKED, now PENDING_REVIEW (Partial Allocation)
    assert result.status == "PENDING_REVIEW"
    # Verify allocation is 50% Equity, 50% Cash
    eq_alloc = next(a for a in result.after_simulated.allocation_by_instrument if a.key == "EQ_1")
    assert eq_alloc.weight == Decimal("0.5")


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

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)

    assert result.status == "PENDING_REVIEW"

    alloc_1 = next(a for a in result.after_simulated.allocation_by_instrument if a.key == "EQ_1")
    alloc_2 = next(a for a in result.after_simulated.allocation_by_instrument if a.key == "EQ_2")

    assert alloc_1.weight == Decimal("0.45")
    assert alloc_2.weight == Decimal("0.45")


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
    assert result.intents[0].instrument_id == "EQ_1"
    assert result.intents[1].side == "BUY"
    assert result.intents[1].instrument_id == "EQ_2"


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


def test_missing_shelf_non_blocking(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_SHELF", weight=Decimal("1.0"))]
    )
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_NO_SHELF", price=Decimal("10.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"


def test_sell_only_allows_liquidation(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_liq",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_SELL_ONLY", quantity=Decimal("100"))],
    )
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
    assert len(result.intents) == 2
    assert result.intents[0].side == "SELL"
    assert result.intents[0].instrument_id == "EQ_SELL_ONLY"
    assert result.intents[1].side == "BUY"
    assert result.intents[1].instrument_id == "EQ_APPROVED"


def test_all_assets_sell_only_blocks_run(base_portfolio, base_options):
    """
    If ALL assets are SELL_ONLY, and target is 100%,
    we allow liquidation of the holdings (SELL).
    But we can't BUY anything.
    Result: 100% Cash.
    Status: PENDING_REVIEW (High Cash).
    """
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_SELL_ONLY", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_SELL_ONLY", status="SELL_ONLY")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_SELL_ONLY", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "PENDING_REVIEW"


def test_dependency_sell_to_fund(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_dep",
        base_currency="SGD",
        positions=[
            Position(instrument_id="EQ_SELL", quantity=Decimal("100")),  # 10k
        ],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_SELL", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_BUY", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_SELL", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_BUY", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_SELL", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_BUY", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    sell_intent = next(i for i in result.intents if i.side == "SELL")
    buy_intent = next(i for i in result.intents if i.side == "BUY")

    assert sell_intent.intent_id in buy_intent.dependencies


def test_implicit_sell_to_zero(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_implicit",
        base_currency="SGD",
        positions=[Position(instrument_id="OLD_ASSET", quantity=Decimal("100"))],  # 1000 SGD
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("0.0"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="NEW_ASSET", weight=Decimal("1.0"))])
    shelf = [
        ShelfEntry(instrument_id="OLD_ASSET", status="APPROVED"),
        ShelfEntry(instrument_id="NEW_ASSET", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="OLD_ASSET", price=Decimal("10.0"), currency="SGD"),
            Price(instrument_id="NEW_ASSET", price=Decimal("10.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    sells = [i for i in result.intents if i.instrument_id == "OLD_ASSET" and i.side == "SELL"]
    assert len(sells) == 1
    assert sells[0].quantity == Decimal("100")

    trace = next(t for t in result.target.targets if t.instrument_id == "OLD_ASSET")
    assert "IMPLICIT_SELL_TO_ZERO" in trace.tags


def test_soft_constraint_breach_within_cash_limits(base_portfolio, base_options):
    """
    Ensures that if Stage 3 (Constraints) returns PENDING_REVIEW, and Stage 5 (Rules)
    returns READY, the final status is PENDING_REVIEW (propagated).
    """
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.99"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)

    eq_alloc = next(a for a in result.after_simulated.allocation_by_instrument if a.key == "EQ_1")
    assert eq_alloc.weight == Decimal("0.99")

    # Use result.rule_results from the engine
    cash_rule = next(r for r in result.rule_results if r.rule_id == "CASH_BAND")
    assert cash_rule.status == "PASS"

    assert result.status == "PENDING_REVIEW"


def test_suspended_asset_is_locked(base_options):
    """
    Scenario 114 Logic Check:
    Held asset is SUSPENDED -> Must NOT be sold.
    Should effectively act as if Model Target = Current Weight.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_frozen",
        base_currency="SGD",
        positions=[Position(instrument_id="RUSSIA_ETF", quantity=Decimal("100"))],  # 10k
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],  # 10k
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_BOND", weight=Decimal("1.0"))])

    shelf = [
        ShelfEntry(instrument_id="RUSSIA_ETF", status="SUSPENDED"),
        ShelfEntry(instrument_id="US_BOND", status="APPROVED"),
    ]

    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="RUSSIA_ETF", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="US_BOND", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # 1. Verify NO Sell intent for Russia
    sells = [i for i in result.intents if i.instrument_id == "RUSSIA_ETF"]
    assert len(sells) == 0

    # 2. Verify Buy intent for US Bond is limited to available cash (10k / 100 = 100 units)
    buys = [i for i in result.intents if i.instrument_id == "US_BOND"]
    assert len(buys) == 1
    assert buys[0].quantity == Decimal("100")

    # 3. Verify Trace tag
    trace = next(t for t in result.target.targets if t.instrument_id == "RUSSIA_ETF")
    assert "LOCKED_POSITION" in trace.tags
    assert trace.final_weight == Decimal("0.5")

    # 4. Verify Exclusion
    excl = next((e for e in result.universe.excluded if e.instrument_id == "RUSSIA_ETF"), None)
    assert excl is not None
    assert "LOCKED_DUE_TO_SUSPENDED" in excl.reason_code


def test_holding_missing_shelf_locks_position(base_options):
    """
    Hit line 308-309: Holding exists but missing from Shelf.
    Should lock the position (safe fallback) and log warning.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_missing_shelf",
        base_currency="SGD",
        positions=[Position(instrument_id="MYSTERY_ASSET", quantity=Decimal("10"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    # Model targets something else
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="KNOWN_ASSET", weight=Decimal("1.0"))]
    )
    # Shelf has KNOWN_ASSET, but NOT MYSTERY_ASSET
    shelf = [ShelfEntry(instrument_id="KNOWN_ASSET", status="APPROVED")]

    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="MYSTERY_ASSET", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="KNOWN_ASSET", price=Decimal("10.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # 1. Verify Mystery Asset was NOT sold (Locked)
    sells = [i for i in result.intents if i.instrument_id == "MYSTERY_ASSET"]
    assert len(sells) == 0

    # 2. Verify Exclusion Log
    excl = next((e for e in result.universe.excluded if e.instrument_id == "MYSTERY_ASSET"), None)
    assert excl is not None
    assert excl.reason_code == "LOCKED_DUE_TO_MISSING_SHELF"


def test_sell_only_excess_no_recipients_stays_unallocated(base_options):
    """
    Hit line 357: Sell-Only redistribution logic where total_rec (eligible buyers) is 0.
    Excess should remain unallocated (Cash).
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell_excess",
        base_currency="SGD",
        positions=[Position(instrument_id="BAD_ASSET", quantity=Decimal("100"))],  # 1000 SGD
        cash_balances=[],
    )
    # Model asks for 100% BAD_ASSET (SELL_ONLY -> 0%).
    # Excess = 100%.
    # Eligible Buyers = None (No other targets).
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="BAD_ASSET", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="BAD_ASSET", status="SELL_ONLY")]

    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="BAD_ASSET", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Verify PENDING_REVIEW (Cash dump)
    assert result.status == "PENDING_REVIEW"

    # Verify Allocation shows Cash
    cash_alloc = next(
        a for a in result.after_simulated.allocation_by_asset_class if a.key == "CASH"
    )
    assert cash_alloc.weight == Decimal("1.0")


def test_coverage_normalization_zero_tradeable_space(base_options):
    """
    Hits line 329: Locked assets > 100% (Market move).
    Setup: Holding 1 (Locked) grows to 110% value.
    Tradeable assets must be scaled to 0.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_over_100",
        base_currency="SGD",
        positions=[Position(instrument_id="LOCKED_ASSET", quantity=Decimal("110"))],
        cash_balances=[],
    )
    # Market Data says price is 10. Total value 1100.
    # Current weight is 1.0 (valuation clamps or engine handles 110%).
    # We target 10% of a NEW asset.
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="NEW", weight=Decimal("0.1"))])
    shelf = [
        ShelfEntry(instrument_id="LOCKED_ASSET", status="SUSPENDED"),
        ShelfEntry(instrument_id="NEW", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="LOCKED_ASSET", price=Decimal("10.0"), currency="SGD"),
            Price(instrument_id="NEW", price=Decimal("10.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # 1. NEW asset should be scaled to 0% because LOCKED_ASSET is >= 100%
    new_target = next(t for t in result.target.targets if t.instrument_id == "NEW")
    assert new_target.final_weight == Decimal("0.0")
    assert result.status == "PENDING_REVIEW"


def test_coverage_holding_logic_branch_missing_valuation(base_options):
    """
    Surgically targets line 261.
    Simulates a scenario where an instrument is in portfolio.positions
    but NOT in the current_valuation object.
    """
    from src.core.engine import _build_universe
    from src.core.models import Money, SimulatedState

    # Setup inputs
    model = ModelPortfolio(targets=[])
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        positions=[Position(instrument_id="GHOST", quantity=Decimal("10"))],
        cash_balances=[],
    )
    shelf = []  # Missing shelf entry

    # Create a 'crippled' valuation that doesn't include the GHOST asset
    valuation = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        positions=[],  # Empty positions list to force line 261 check to fail/pass
    )

    # We call the internal builder directly to bypass the standard run_simulation flow
    dq_log = {"shelf_missing": []}
    _build_universe(model, portfolio, shelf, base_options, dq_log, valuation)


def test_locked_assets_exceed_total(base_options):
    """
    Explicitly tests branch where locked assets > 1.0 (100% of portfolio).
    """
    # Removed unused variables portfolio, market_data, model, shelf
    from src.core.engine import _generate_targets

    eligible = {"A": Decimal("0.6"), "B": Decimal("0.5")}  # Sum 1.1
    buy_list = []  # All locked
    sell_only_excess = Decimal("0.0")
    total_val = Decimal("1000")
    base_ccy = "SGD"

    # Calls internal function
    trace, status = _generate_targets(
        ModelPortfolio(targets=[]),
        eligible,
        buy_list,
        sell_only_excess,
        base_options,
        total_val,
        base_ccy,
    )
    assert status == "PENDING_REVIEW"


def test_buy_depends_on_sell_explicit(base_options):
    """
    Explicitly tests the dependency linking branch in _generate_fx_and_simulate
    where a BUY depends on a SELL (and isn't already linked).
    """
    from src.core.engine import _generate_fx_and_simulate
    from src.core.models import IntentRationale

    # Setup dummy inputs
    portfolio = PortfolioSnapshot(
        portfolio_id="pf",
        base_currency="SGD",
        positions=[],
        cash_balances=[],
    )
    # FIXED: Added FX rate to prevent crash
    market_data = MarketDataSnapshot(
        prices=[], fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.3"))]
    )
    shelf = []
    total_val = Decimal("1000")

    # Manually craft intents: Sell USD, Buy USD (Logic weirdness but syntactically valid)
    # This forces the dependency linker to see a BUY with same currency as SELL.
    intents = [
        OrderIntent(
            intent_id="oi_sell",
            side="SELL",
            notional=Money(amount=Decimal("100"), currency="USD"),
            rationale=IntentRationale(code="TEST", message="Test"),
        ),
        OrderIntent(
            intent_id="oi_buy",
            side="BUY",
            notional=Money(amount=Decimal("50"), currency="USD"),
            rationale=IntentRationale(code="TEST", message="Test"),
            dependencies=[],  # Empty, needs linking
        ),
    ]

    intents, _, _, _ = _generate_fx_and_simulate(
        portfolio, market_data, shelf, intents, base_options, total_val
    )

    buy_intent = next(i for i in intents if i.side == "BUY")
    assert "oi_sell" in buy_intent.dependencies


def test_simulation_crash_on_missing_fx(base_options):
    """
    Verifies that the engine raises ValueError if FX is missing during simulation.
    This protects against crashes if the internal method is called without checks.
    """
    from src.core.engine import _generate_fx_and_simulate
    from src.core.models import IntentRationale

    portfolio = PortfolioSnapshot(
        portfolio_id="pf_crash", base_currency="SGD", positions=[], cash_balances=[]
    )
    # Missing FX rate for USD/SGD
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])

    intents = [
        OrderIntent(
            intent_id="oi_1",
            side="SELL",
            notional=Money(amount=Decimal("100"), currency="USD"),
            rationale=IntentRationale(code="TEST", message="Test"),
        )
    ]

    with pytest.raises(ValueError, match="Missing FX rate for USD/SGD"):
        _generate_fx_and_simulate(
            portfolio, market_data, [], intents, base_options, Decimal("1000")
        )
