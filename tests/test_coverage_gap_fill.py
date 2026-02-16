"""
FILE: tests/test_coverage_gap_fill.py
GOAL: Hit the remaining code coverage in engine.py.
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
    PortfolioSnapshot,
    Position,
    Price,
    SecurityTradeIntent,
    ShelfEntry,
    ValuationMode,
)
from src.core.valuation import build_simulated_state


@pytest.fixture
def base_inputs():
    pf = PortfolioSnapshot(
        portfolio_id="gap_fill",
        base_currency="USD",
        positions=[Position(instrument_id="LOCKED_ASSET", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="JPY", amount=Decimal("1000"))],
    )
    mkt = MarketDataSnapshot(
        prices=[
            Price(instrument_id="LOCKED_ASSET", price=Decimal("10"), currency="USD"),
            Price(instrument_id="TARGET_ASSET", price=Decimal("10"), currency="USD"),
        ],
        fx_rates=[FxRate(pair="JPY/USD", rate=Decimal("0.01"))],
    )
    shelf = [
        ShelfEntry(instrument_id="LOCKED_ASSET", status="RESTRICTED"),
        ShelfEntry(instrument_id="TARGET_ASSET", status="APPROVED"),
    ]
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="TARGET_ASSET", weight=Decimal("0.5"))]
    )
    return pf, mkt, model, shelf


def test_engine_restricted_logic(base_inputs):
    """Hits engine.py:79-81 (Restricted logic)."""
    pf, mkt, model, shelf = base_inputs
    result = run_simulation(pf, mkt, model, shelf, EngineOptions(allow_restricted=False))
    excl = next(
        (e for e in result.universe.excluded if e.instrument_id == "LOCKED_ASSET"), None
    )
    assert excl is not None
    assert "LOCKED_DUE_TO_RESTRICTED" in excl.reason_code


def test_reconciliation_failure_block(base_inputs):
    """Hits engine.py:413-424 (Reconciliation Hard Fail)."""
    pf, mkt, model, shelf = base_inputs
    pf.positions[0].market_value = Money(amount=Decimal("9999999"), currency="USD")
    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT),
    )
    # With the fix in engine.py, this should now be BLOCKED
    assert result.status == "BLOCKED"
    blocker = next(r for r in result.rule_results if r.rule_id == "RECONCILIATION")
    assert blocker.status == "FAIL"


def test_valuation_missing_fx_log(base_inputs):
    """Hits valuation.py:157 & 192 (Missing FX paths)."""
    pf, mkt, model, shelf = base_inputs
    pf.positions.append(Position(instrument_id="NO_FX_ASSET", quantity=Decimal("10")))
    mkt.prices.append(
        Price(instrument_id="NO_FX_ASSET", price=Decimal("100"), currency="KRW")
    )
    pf.cash_balances.append(CashBalance(currency="KRW", amount=Decimal("500")))
    dq = {}
    warns = []
    build_simulated_state(pf, mkt, shelf, dq, warns)
    assert "KRW/USD" in dq["fx_missing"]


def test_dependency_linking_explicit(base_inputs):
    """Hits engine.py:283-292 (Dependency Linking Edge Cases)."""
    pf = PortfolioSnapshot(
        portfolio_id="dep_test",
        base_currency="USD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("1000"))],
    )
    mkt = MarketDataSnapshot(
        prices=[Price(instrument_id="GBP_STK", price=Decimal("100"), currency="GBP")],
        fx_rates=[FxRate(pair="GBP/USD", rate=Decimal("1.2"))],
    )
    shelf = [ShelfEntry(instrument_id="GBP_STK", status="APPROVED")]
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="GBP_STK", weight=Decimal("1.0"))]
    )
    result = run_simulation(pf, mkt, model, shelf, EngineOptions())
    buy = next(
        i
        for i in result.intents
        if isinstance(i, SecurityTradeIntent) and i.side == "BUY"
    )
    assert len(buy.dependencies) > 0


# --- NEW TESTS FOR 100% COVERAGE ---


def test_universe_suspended_exclusion(base_inputs):
    """Hits engine.py:43-44 (Suspended/Banned in Model)."""
    pf, mkt, _, shelf = base_inputs
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="SUSPENDED_ASSET", weight=Decimal("0.1"))]
    )
    shelf.append(ShelfEntry(instrument_id="SUSPENDED_ASSET", status="SUSPENDED"))

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    excl = next(
        (e for e in result.universe.excluded if e.instrument_id == "SUSPENDED_ASSET"), None
    )
    assert excl is not None
    assert "SHELF_STATUS_SUSPENDED" in excl.reason_code


def test_universe_missing_shelf_locked(base_inputs):
    """Hits engine.py:81-83 (Held asset missing from Shelf)."""
    pf, mkt, model, shelf = base_inputs
    pf.positions.append(Position(instrument_id="GHOST_ASSET", quantity=Decimal("10")))
    mkt.prices.append(
        Price(instrument_id="GHOST_ASSET", price=Decimal("100"), currency="USD")
    )

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    excl = next(
        (e for e in result.universe.excluded if e.instrument_id == "GHOST_ASSET"), None
    )
    assert excl is not None
    assert "LOCKED_DUE_TO_MISSING_SHELF" in excl.reason_code


def test_target_locked_over_100(base_inputs):
    """Hits engine.py:126 (Locked > 100%)."""
    pf, mkt, model, shelf = base_inputs
    pf.positions = [
        Position(instrument_id="LOCKED_ASSET", quantity=Decimal("1000"))
    ]  # 10k val
    mkt.prices[0].price = Decimal("1000")  # Now 1M val!

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert result.status == "PENDING_REVIEW"


def test_min_cash_buffer_scaling(base_inputs):
    """Hits engine.py:150 (Cash Buffer Scaling)."""
    pf, mkt, model, shelf = base_inputs
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="TARGET_ASSET", weight=Decimal("1.0"))]
    )

    # Require 10% Cash Buffer
    result = run_simulation(
        pf, mkt, model, shelf, EngineOptions(min_cash_buffer_pct=Decimal("0.10"))
    )

    # Target should be scaled down to 0.9
    tgt = next(t for t in result.target.targets if t.instrument_id == "TARGET_ASSET")
    assert tgt.final_weight <= Decimal("0.91")
    assert result.status == "PENDING_REVIEW"


def test_dependency_sell_linking(base_inputs):
    """Hits engine.py:285-294 (Security Sell -> Security Buy Dependency)."""
    pf = PortfolioSnapshot(
        portfolio_id="p_chain",
        base_currency="USD",
        positions=[Position(instrument_id="GBP_STK", quantity=Decimal("10"))],
        cash_balances=[],
    )
    mkt = MarketDataSnapshot(
        prices=[
            Price(instrument_id="GBP_STK", price=Decimal("100"), currency="GBP"),
            Price(instrument_id="GBP_STK_B", price=Decimal("100"), currency="GBP"),
        ],
        fx_rates=[
            FxRate(pair="GBP/USD", rate=Decimal("1.2")),
        ],
    )
    shelf = [
        ShelfEntry(instrument_id="GBP_STK", status="APPROVED"),
        ShelfEntry(instrument_id="GBP_STK_B", status="APPROVED"),
    ]
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="GBP_STK_B", weight=Decimal("1.0")),  # Buy
            ModelTarget(instrument_id="GBP_STK", weight=Decimal("0.0")),  # Sell
        ]
    )

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    buy = next(i for i in result.intents if i.instrument_id == "GBP_STK_B")
    sell = next(i for i in result.intents if i.instrument_id == "GBP_STK")

    # The Buy should depend on the Sell because same currency and cash is tight
    assert sell.intent_id in buy.dependencies


def test_hard_fail_shorting(base_inputs):
    """Hits engine.py:431 (NO_SHORTING Hard Fail)."""
    pf, mkt, model, shelf = base_inputs
    pf.positions.append(Position(instrument_id="SHORT_POS", quantity=Decimal("-10")))
    mkt.prices.append(
        Price(instrument_id="SHORT_POS", price=Decimal("100"), currency="USD")
    )
    shelf.append(ShelfEntry(instrument_id="SHORT_POS", status="APPROVED"))

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings


def test_soft_fail_status(base_inputs):
    """Hits engine.py:438 (Soft Fail -> PENDING_REVIEW)."""
    pf, mkt, model, shelf = base_inputs
    # Trigger Cash Band Soft Fail (Min Cash 5%)
    result = run_simulation(
        pf, mkt, model, shelf, EngineOptions(cash_band_min_weight=Decimal("0.05"))
    )

    assert result.status == "PENDING_REVIEW"