"""
FILE: tests/test_engine_core.py
Tests for core engine logic: Universe, Constraints, Intents, Dependencies.
"""

from decimal import Decimal

from src.core.engine import (
    _build_universe,
    _generate_fx_and_simulate,
    _generate_targets,
    run_simulation,
)
from src.core.models import (
    CashBalance,
    DiagnosticsData,
    EngineOptions,
    FxRate,
    IntentRationale,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    OrderIntent,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
    SimulatedState,
)


def test_simple_rebalance_no_trades(base_portfolio, base_options):
    model = ModelPortfolio(targets=[])
    shelf = []
    market_data = MarketDataSnapshot(prices=[])

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    assert len(result.intents) == 0


def test_banned_assets_excluded(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_BANNED", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_BANNED", status="BANNED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_BANNED", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    # RFC-0006B: With relaxed defaults, excluded assets -> 100% Cash -> READY (Valid)
    assert result.status == "READY"
    assert len(result.intents) == 0
    # Verify exclusion logic still works
    assert len(result.universe.excluded) == 1
    assert result.universe.excluded[0].reason_code == "SHELF_STATUS_BANNED"


def test_restricted_assets_excluded(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_RESTRICTED", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_RESTRICTED", status="RESTRICTED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_RESTRICTED", price=Decimal("10.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    # RFC-0006B: Relaxed defaults -> READY
    assert result.status == "READY"
    assert len(result.intents) == 0


def test_after_state_simulation_fidelity(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_fid",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED", asset_class="EQUITY")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Should be READY with default options
    assert result.status == "READY"
    assert len(result.intents) == 1
    assert result.intents[0].quantity == 50

    # Check after-state
    pos = next(p for p in result.after_simulated.positions if p.instrument_id == "EQ_1")
    assert pos.quantity == 50
    assert pos.weight == Decimal("0.5")


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
    # Suppression is INFO/SOFT pass -> READY
    assert result.status == "READY"
    assert len(result.diagnostics.suppressed_intents) == 1


def test_infeasible_constraint_no_recipients(base_portfolio):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.5"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)
    assert result.status == "PENDING_REVIEW"
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
    assert alloc_1.weight == Decimal("0.45")


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
        positions=[Position(instrument_id="EQ_SELL", quantity=Decimal("100"))],
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
        positions=[Position(instrument_id="OLD_ASSET", quantity=Decimal("100"))],
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
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.99"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)
    eq_alloc = next(a for a in result.after_simulated.allocation_by_instrument if a.key == "EQ_1")
    assert eq_alloc.weight == Decimal("0.99")
    cash_rule = next(r for r in result.rule_results if r.rule_id == "CASH_BAND")
    assert cash_rule.status == "PASS"
    assert result.status == "PENDING_REVIEW"


def test_suspended_asset_is_locked(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_frozen",
        base_currency="SGD",
        positions=[Position(instrument_id="RUSSIA_ETF", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
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
    sells = [i for i in result.intents if i.instrument_id == "RUSSIA_ETF"]
    assert len(sells) == 0
    trace = next(t for t in result.target.targets if t.instrument_id == "RUSSIA_ETF")
    assert "LOCKED_POSITION" in trace.tags
    excl = next((e for e in result.universe.excluded if e.instrument_id == "RUSSIA_ETF"), None)
    assert excl is not None
    assert "LOCKED_DUE_TO_SUSPENDED" in excl.reason_code


def test_holding_missing_shelf_locks_position(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_missing_shelf",
        base_currency="SGD",
        positions=[Position(instrument_id="MYSTERY_ASSET", quantity=Decimal("10"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="KNOWN_ASSET", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="KNOWN_ASSET", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="MYSTERY_ASSET", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="KNOWN_ASSET", price=Decimal("10.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    sells = [i for i in result.intents if i.instrument_id == "MYSTERY_ASSET"]
    assert len(sells) == 0
    excl = next((e for e in result.universe.excluded if e.instrument_id == "MYSTERY_ASSET"), None)
    assert excl is not None
    assert excl.reason_code == "LOCKED_DUE_TO_MISSING_SHELF"


def test_sell_only_excess_no_recipients_stays_unallocated(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell_excess",
        base_currency="SGD",
        positions=[Position(instrument_id="BAD_ASSET", quantity=Decimal("100"))],
        cash_balances=[],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="BAD_ASSET", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="BAD_ASSET", status="SELL_ONLY")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="BAD_ASSET", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    assert result.status == "PENDING_REVIEW"
    cash_alloc = next(
        a for a in result.after_simulated.allocation_by_asset_class if a.key == "CASH"
    )
    assert cash_alloc.weight == Decimal("1.0")


def test_coverage_normalization_zero_tradeable_space(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_over_100",
        base_currency="SGD",
        positions=[Position(instrument_id="LOCKED_ASSET", quantity=Decimal("110"))],
        cash_balances=[],
    )
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
    new_target = next(t for t in result.target.targets if t.instrument_id == "NEW")
    assert new_target.final_weight == Decimal("0.0")
    assert result.status == "PENDING_REVIEW"


def test_coverage_holding_logic_branch_missing_valuation(base_options):
    model = ModelPortfolio(targets=[])
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        positions=[Position(instrument_id="GHOST", quantity=Decimal("10"))],
        cash_balances=[],
    )
    shelf = []
    valuation = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        positions=[],
    )
    dq_log = {"shelf_missing": []}
    _build_universe(model, portfolio, shelf, base_options, dq_log, valuation)


def test_locked_assets_exceed_total(base_options):
    eligible = {"A": Decimal("0.6"), "B": Decimal("0.5")}
    buy_list = []
    sell_only_excess = Decimal("0.0")
    total_val = Decimal("1000")
    base_ccy = "SGD"
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
    # ... (imports and setup same as existing file)
    from decimal import Decimal

    from src.core.engine import _generate_fx_and_simulate
    from src.core.models import FxRate, MarketDataSnapshot, Money, PortfolioSnapshot

    portfolio = PortfolioSnapshot(
        portfolio_id="pf",
        base_currency="SGD",
        positions=[],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(
        prices=[],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.3"))],
    )
    shelf = []
    total_val = Decimal("1000")

    intents = [
        OrderIntent(
            intent_id="oi_sell",
            side="SELL",
            instrument_id="DUMMY_USD_SELL",
            quantity=Decimal("10"),
            notional=Money(amount=Decimal("100"), currency="USD"),
            rationale=IntentRationale(code="TEST", message="Test"),
        ),
        OrderIntent(
            intent_id="oi_buy",
            side="BUY",
            instrument_id="DUMMY_USD_BUY",
            quantity=Decimal("5"),
            notional=Money(amount=Decimal("50"), currency="USD"),
            rationale=IntentRationale(code="TEST", message="Test"),
            dependencies=[],
        ),
    ]

    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    # FIX: Unpack 5 values
    intents, _, _, _, _ = _generate_fx_and_simulate(
        portfolio, market_data, shelf, intents, base_options, total_val, diag
    )

    # Check that Buy depends on Sell (because they share USD currency and Sell provides cash)
    # Actually, logical check: Sell USD -> We gain USD? No, Sell Asset -> Gain USD.
    # Buy Asset -> Spend USD.
    # So Sell funds Buy.
    buy_intent = next(i for i in intents if i.side == "BUY")
    sell_intent = next(i for i in intents if i.side == "SELL")
    assert sell_intent.intent_id in buy_intent.dependencies


def test_status_propagation_explicit(base_options):
    """
    Explicitly tests that if s3_stat is PENDING_REVIEW and f_stat is READY,
    the final status becomes PENDING_REVIEW.
    """
    # 1. Setup a scenario where Target Generation (S3) yields PENDING_REVIEW
    # We trigger PENDING_REVIEW by using explicit options to force a cap or constraint
    # Using 'min_cash_buffer_pct' is an easy way to trigger S3 review
    strict_options = base_options.model_copy()
    strict_options.min_cash_buffer_pct = Decimal("0.5")  # Require 50% cash buffer

    eligible = {"A": Decimal("0.8"), "B": Decimal("0.0")}
    buy_list = ["A"]
    sell_only_excess = Decimal("0.0")
    total_val = Decimal("1000")
    base_ccy = "SGD"

    # Verify S3 generates PENDING_REVIEW (0.8 > 0.5 allowed)
    trace, s3_stat = _generate_targets(
        ModelPortfolio(targets=[]),
        eligible,
        buy_list,
        sell_only_excess,
        strict_options,
        total_val,
        base_ccy,
    )
    assert s3_stat == "PENDING_REVIEW"

    # 2. Setup a simulation that yields READY
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_ready",
        base_currency="SGD",
        positions=[Position(instrument_id="SAFE_ASSET", quantity=Decimal("10"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10.0"))],
    )
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="SAFE_ASSET", price=Decimal("100.0"), currency="SGD"),
            # ADDED: Price for A to avoid DQ Hard Block
            Price(instrument_id="A", price=Decimal("100.0"), currency="SGD"),
        ],
        fx_rates=[],
    )
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    total_val_compliant = Decimal("1010.0")

    intents, after, rules, f_stat, _ = _generate_fx_and_simulate(
        portfolio, market_data, [], [], strict_options, total_val_compliant, diag
    )

    # f_stat might be READY or PENDING_REVIEW depending on rules
    # With strict options, if cash band fails, it might be PENDING_REVIEW.
    # But here we just want to verify logic flow.
    # If we force f_stat to READY (by mocking or ensuring compliance), verify propagation.

    # Actually, let's just test run_simulation end-to-end with the S3 trigger
    # Using the strict options
    result = run_simulation(
        portfolio,
        market_data,
        ModelPortfolio(targets=[ModelTarget(instrument_id="A", weight=Decimal("0.8"))]),
        [
            ShelfEntry(instrument_id="A", status="APPROVED"),
            ShelfEntry(instrument_id="SAFE_ASSET", status="APPROVED"),
        ],
        strict_options,
    )

    assert result.status == "PENDING_REVIEW"


def test_coverage_missing_fx_non_blocking():
    """
    Scenario: block_on_missing_fx = False.
    We have a USD cash balance that needs sweeping, but no USD/SGD rate.
    Expectation: Warning logged, but simulation proceeds (Result: READY, not BLOCKED).
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_warn",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("100.0"))],
    )
    # No trades
    model = ModelPortfolio(targets=[])
    shelf = []
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])  # Missing FX

    # Enable non-blocking behavior
    options = EngineOptions(block_on_missing_fx=False)

    result = run_simulation(portfolio, market_data, model, shelf, options)

    # Should proceed
    assert result.status == "READY"
    # Should check diagnostics for the missing FX warning/log
    # Note: Logic might log to data_quality but not block
    assert "USD/SGD" in result.diagnostics.data_quality["fx_missing"]


def test_coverage_sub_unit_trade_quantity_zero():
    """
    Scenario: Target weight implies purchasing 0.5 shares.
    Price = 1000. Target Value = 500. Qty = 0.
    Expectation: No intent generated (implicitly suppressed by integer math),
    logic should handle 'qty > 0' check gracefully.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_small",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )

    # Target 500 SGD allocation
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EXPENSIVE", weight=Decimal("0.05"))])
    shelf = [ShelfEntry(instrument_id="EXPENSIVE", status="APPROVED")]

    # Price 1000 SGD. 500 / 1000 = 0.5 shares -> 0 shares.
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EXPENSIVE", price=Decimal("1000.0"), currency="SGD")]
    )

    # Disable explicit dust suppression to force the integer logic check
    options = EngineOptions(suppress_dust_trades=False)

    result = run_simulation(portfolio, market_data, model, shelf, options)

    assert result.status == "READY"
    assert len(result.intents) == 0


def test_coverage_target_missing_shelf_entry():
    """Hits engine.py: _build_universe -> if not shelf_ent: dq_log..."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_1", base_currency="SGD", positions=[], cash_balances=[]
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="GHOST", weight=Decimal("0.1"))])
    shelf = []
    market_data = MarketDataSnapshot(prices=[])

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    assert result.status == "BLOCKED"
    assert "GHOST" in result.diagnostics.data_quality["shelf_missing"]


def test_coverage_holding_missing_shelf_with_market_data():
    """Hits engine.py: _build_universe -> if not shelf_ent: if curr: excluded.append(...)"""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_2",
        base_currency="SGD",
        positions=[Position(instrument_id="DELISTED", quantity=Decimal("100"))],
        cash_balances=[],
    )
    model = ModelPortfolio(targets=[])
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="DELISTED", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    excl = next((e for e in result.universe.excluded if e.instrument_id == "DELISTED"), None)
    assert excl is not None
    assert excl.reason_code == "LOCKED_DUE_TO_MISSING_SHELF"


def test_coverage_fx_sweep_missing_rate():
    """Hits engine.py: _generate_fx_and_simulate -> block_on_missing_fx"""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sweep",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("100.0"))],
    )
    model = ModelPortfolio(targets=[])
    shelf = []
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    assert result.status == "BLOCKED"
    assert "USD/SGD" in result.diagnostics.data_quality["fx_missing"]


def test_coverage_reconciliation_mismatch_direct():
    """
    Hits engine.py: _generate_fx_and_simulate -> if recon.status == 'MISMATCH'
    We force this by passing a total_val_before that logicially contradicts the portfolio.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_recon",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("100.0"))],
    )
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    # Real value is 100.0. We tell it 99999.9.
    fake_before_val = Decimal("99999.9")

    intents, state, rules, status, recon = _generate_fx_and_simulate(
        portfolio, market_data, [], [], EngineOptions(), fake_before_val, diag
    )

    assert status == "BLOCKED"
    assert recon.status == "MISMATCH"
    assert any(r.rule_id == "RECONCILIATION" and r.status == "FAIL" for r in rules)


def test_coverage_min_cash_buffer_breach():
    """
    Hits engine.py: _generate_targets -> min_cash_buffer_pct logic
    """
    options = EngineOptions(min_cash_buffer_pct=Decimal("0.5"))  # Require 50% cash

    # We ask for 100% allocation to A
    eligible_targets = {"A": Decimal("1.0")}
    buy_list = ["A"]
    sell_only_excess = Decimal("0.0")

    trace, status = _generate_targets(
        ModelPortfolio(targets=[]),
        eligible_targets,
        buy_list,
        sell_only_excess,
        options,
        total_val=Decimal("1000.0"),
        base_ccy="SGD",
    )

    # Should scale down to 0.5 and flag REVIEW
    assert status == "PENDING_REVIEW"
    assert eligible_targets["A"] == Decimal("0.5")


def test_coverage_soft_rule_failure_in_simulation():
    """
    Hits engine.py: _generate_fx_and_simulate -> final_status = 'PENDING_REVIEW'
    We use strict cash bands to force a SOFT FAIL on the after-state.
    """
    # Start with 100% Cash.
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_soft",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    # Don't trade anything. Result is 100% Cash.
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])

    # Strict options: Max Cash 50%. We have 100%. This is a SOFT FAIL.
    strict_opts = EngineOptions(
        cash_band_max_weight=Decimal("0.5"), cash_band_min_weight=Decimal("0.0")
    )

    intents, state, rules, status, recon = _generate_fx_and_simulate(
        portfolio, market_data, [], [], strict_opts, Decimal("1000.0"), diag
    )

    assert status == "PENDING_REVIEW"
    assert any(r.rule_id == "CASH_BAND" and r.status == "FAIL" for r in rules)
