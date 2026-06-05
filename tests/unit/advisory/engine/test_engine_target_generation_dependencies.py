import importlib
from decimal import Decimal
from types import SimpleNamespace

from src.core import target_generation
from src.core.models import DiagnosticsData, EngineOptions, ShelfEntry


def test_load_target_solver_dependencies_returns_none_when_solver_stack_is_unavailable(
    monkeypatch,
):
    def unavailable_import(name: str):
        if name == "cvxpy":
            raise ImportError("cvxpy unavailable")
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(importlib, "import_module", unavailable_import)

    assert target_generation.load_target_solver_dependencies() is None


def test_load_target_solver_dependencies_returns_imported_solver_modules(monkeypatch):
    cvxpy_module = SimpleNamespace(__name__="cvxpy")
    numpy_module = SimpleNamespace(__name__="numpy")

    def import_module(name: str):
        if name == "cvxpy":
            return cvxpy_module
        if name == "numpy":
            return numpy_module
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(importlib, "import_module", import_module)

    dependencies = target_generation.load_target_solver_dependencies()

    assert dependencies is not None
    assert dependencies[0] is cvxpy_module
    assert dependencies[1] is numpy_module


def test_generate_targets_solver_blocks_with_diagnostic_when_solver_stack_is_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(target_generation, "load_target_solver_dependencies", lambda: None)
    diagnostics = DiagnosticsData(data_quality={})

    targets, status = target_generation.generate_targets_solver(
        model=None,
        eligible_targets={},
        buy_list=[],
        sell_only_excess=Decimal("0"),
        shelf=[],
        options=EngineOptions(),
        total_val=Decimal("0"),
        base_ccy="USD",
        diagnostics=diagnostics,
    )

    assert targets == []
    assert status == "BLOCKED"
    assert diagnostics.warnings == ["SOLVER_ERROR"]


def test_collect_infeasibility_hints_reports_cash_band_and_capacity_limits() -> None:
    hints = target_generation._collect_infeasibility_hints(
        tradeable_ids=["AAPL"],
        locked_weight=Decimal("0.20"),
        options=EngineOptions(
            cash_band_min_weight=Decimal("0.40"),
            cash_band_max_weight=Decimal("0.10"),
            single_position_max_weight=Decimal("0.20"),
        ),
        eligible_targets={"AAPL": Decimal("0.80")},
        shelf=[ShelfEntry(instrument_id="AAPL", status="APPROVED")],
    )

    assert hints == [
        "INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION",
        "INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY",
    ]


def test_collect_infeasibility_hints_reports_locked_group_weight() -> None:
    hints = target_generation._collect_infeasibility_hints(
        tradeable_ids=["BOND_A"],
        locked_weight=Decimal("0.30"),
        options=EngineOptions(
            group_constraints={"sector:TECH": {"max_weight": "0.25"}},
        ),
        eligible_targets={
            "BOND_A": Decimal("0.20"),
            "TECH_LOCKED": Decimal("0.30"),
        },
        shelf=[
            ShelfEntry(
                instrument_id="BOND_A",
                status="APPROVED",
                attributes={"sector": "BOND"},
            ),
            ShelfEntry(
                instrument_id="TECH_LOCKED",
                status="SELL_ONLY",
                attributes={"sector": "TECH"},
            ),
        ],
    )

    assert hints == ["INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_sector:TECH"]
