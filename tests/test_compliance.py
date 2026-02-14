"""
FILE: tests/test_compliance.py
Unit tests for the Rule Engine (RFC-0005).
"""

from decimal import Decimal

from src.core.compliance import RuleEngine
from src.core.models import (
    AllocationMetric,
    EngineOptions,
    Money,
    SimulatedState,
)


def test_cash_band_pass():
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        allocation_by_asset_class=[
            AllocationMetric(
                key="CASH",
                weight=Decimal("0.04"),
                value=Money(amount=Decimal("40"), currency="SGD"),
            )
        ],
    )
    results = RuleEngine.evaluate(state, EngineOptions())
    cash_rule = next(r for r in results if r.rule_id == "CASH_BAND")
    assert cash_rule.status == "PASS"


def test_cash_band_fail():
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        allocation_by_asset_class=[
            AllocationMetric(
                key="CASH",
                weight=Decimal("0.10"),
                value=Money(amount=Decimal("100"), currency="SGD"),
            )
        ],
    )
    results = RuleEngine.evaluate(state, EngineOptions())
    cash_rule = next(r for r in results if r.rule_id == "CASH_BAND")
    assert cash_rule.status == "FAIL"
    assert cash_rule.severity == "SOFT"


def test_single_position_max_fail():
    """Verifies that the Hard Block logic for position drift works."""
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        allocation_by_instrument=[
            AllocationMetric(
                key="APPLE",
                weight=Decimal("0.55"),  # Exceeds 0.50 limit
                value=Money(amount=Decimal("550"), currency="SGD"),
            )
        ],
    )
    options = EngineOptions(single_position_max_weight=Decimal("0.50"))
    results = RuleEngine.evaluate(state, options)

    pos_rule = next(r for r in results if r.rule_id == "SINGLE_POSITION_MAX")
    assert pos_rule.status == "FAIL"
    assert pos_rule.severity == "HARD"
    assert pos_rule.measured == Decimal("0.55")
