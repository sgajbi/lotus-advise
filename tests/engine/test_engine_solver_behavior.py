from decimal import Decimal
from importlib.util import find_spec

import pytest

from src.core.engine import _generate_targets, run_simulation
from src.core.models import DiagnosticsData, EngineOptions, GroupConstraint, ShelfEntry
from tests.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    target,
)


def _diag():
    return DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )


@pytest.mark.skipif(find_spec("cvxpy") is None, reason="cvxpy not installed")
def test_solver_counts_locked_group_weight_in_group_constraint():
    model = model_portfolio(targets=[target("TECH_BUY", "1.0"), target("BOND", "0.0")])
    eligible_targets = {
        "TECH_BUY": Decimal("0.20"),
        "TECH_LOCKED": Decimal("0.20"),
        "BOND": Decimal("0.60"),
    }
    buy_list = ["TECH_BUY", "BOND"]
    shelf = [
        ShelfEntry(instrument_id="TECH_BUY", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="TECH_LOCKED", status="SUSPENDED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="BOND", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
        group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.25"))},
    )

    trace, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert len(trace) == 3
    assert eligible_targets["TECH_BUY"] <= Decimal("0.0500")
    assert eligible_targets["TECH_LOCKED"] == Decimal("0.20")
    assert eligible_targets["BOND"] >= Decimal("0.7500")


@pytest.mark.skipif(find_spec("cvxpy") is None, reason="cvxpy not installed")
def test_solver_warns_unknown_attribute_and_continues():
    model = model_portfolio(targets=[target("A", "0.6"), target("B", "0.4")])
    eligible_targets = {"A": Decimal("0.6"), "B": Decimal("0.4")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    diagnostics = _diag()
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
        group_constraints={"region:EMEA": GroupConstraint(max_weight=Decimal("0.10"))},
    )

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert "UNKNOWN_CONSTRAINT_ATTRIBUTE_region" in diagnostics.warnings


@pytest.mark.skipif(find_spec("cvxpy") is None, reason="cvxpy not installed")
def test_solver_handles_sell_only_excess_with_buy_recipients():
    model = model_portfolio(targets=[target("A", "0.7"), target("B", "0.3")])
    eligible_targets = {"A": Decimal("0.7"), "B": Decimal("0.3")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
    )

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0.2"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert eligible_targets["A"] == Decimal("0.7000")
    assert eligible_targets["B"] == Decimal("0.3000")


@pytest.mark.skipif(find_spec("cvxpy") is None, reason="cvxpy not installed")
def test_solver_skips_group_constraint_when_value_not_present():
    model = model_portfolio(targets=[target("A", "0.7"), target("B", "0.3")])
    eligible_targets = {"A": Decimal("0.7"), "B": Decimal("0.3")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    diagnostics = _diag()
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
        group_constraints={"sector:HEALTH": GroupConstraint(max_weight=Decimal("0.10"))},
    )

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "READY"
    assert diagnostics.warnings == []


@pytest.mark.skipif(find_spec("cvxpy") is None, reason="cvxpy not installed")
def test_solver_falls_back_to_secondary_solver_when_primary_errors(monkeypatch):
    import cvxpy as cp

    model = model_portfolio(targets=[target("A", "0.5"), target("B", "0.5")])
    eligible_targets = {"A": Decimal("0.5"), "B": Decimal("0.5")}
    shelf = [
        ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
    ]
    options = EngineOptions(
        target_method="SOLVER",
        cash_band_min_weight=Decimal("0.0"),
        cash_band_max_weight=Decimal("0.0"),
    )

    original_solve = cp.Problem.solve
    attempted = []

    def solve_with_primary_failure(self, *args, **kwargs):
        solver = kwargs.get("solver")
        attempted.append(str(solver))
        if solver == cp.OSQP:
            raise cp.SolverError("forced primary solver failure")
        return original_solve(self, *args, **kwargs)

    monkeypatch.setattr(cp.Problem, "solve", solve_with_primary_failure)

    _, status = _generate_targets(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=["A", "B"],
        sell_only_excess=Decimal("0"),
        shelf=shelf,
        options=options,
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=_diag(),
    )

    assert status == "READY"
    assert str(cp.OSQP) in attempted
    assert str(cp.SCS) in attempted


@pytest.mark.skipif(find_spec("cvxpy") is None, reason="cvxpy not installed")
def test_run_simulation_solver_preserves_pending_review_when_no_recipients():
    pf = portfolio_snapshot(
        portfolio_id="pf_solver_pending",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    mkt = market_data_snapshot(prices=[price("SELL_ONLY_ASSET", "10", "USD")], fx_rates=[])
    model = model_portfolio(targets=[target("SELL_ONLY_ASSET", "1.0")])
    shelf = [ShelfEntry(instrument_id="SELL_ONLY_ASSET", status="SELL_ONLY")]
    options = EngineOptions(target_method="SOLVER")

    result = run_simulation(pf, mkt, model, shelf, options)

    assert result.status == "PENDING_REVIEW"
    assert result.intents == []


def test_solver_returns_blocked_when_solver_dependencies_unavailable(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def import_without_cvxpy(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "cvxpy":
            raise ImportError("cvxpy unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_cvxpy)

    model = model_portfolio(targets=[target("A", "1.0")])
    diagnostics = _diag()
    trace, status = _generate_targets(
        model=model,
        eligible_targets={"A": Decimal("1.0")},
        buy_list=["A"],
        sell_only_excess=Decimal("0"),
        shelf=[ShelfEntry(instrument_id="A", status="APPROVED")],
        options=EngineOptions(target_method="SOLVER"),
        total_val=Decimal("1000"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert trace == []
    assert "SOLVER_ERROR" in diagnostics.warnings
