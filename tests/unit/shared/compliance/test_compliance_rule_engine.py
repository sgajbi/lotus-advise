"""
FILE: tests/compliance/test_compliance_rule_engine.py
Unit tests for the Rule Engine (RFC-0005/RFC-0006B).
"""

from decimal import Decimal

import pytest

from src.core.compliance import RuleEngine
from src.core.models import (
    AllocationMetric,
    DiagnosticsData,
    EngineOptions,
    Money,
    PositionSummary,
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
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    results = RuleEngine.evaluate(state, EngineOptions(), diag)
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
    strict_options = EngineOptions(
        cash_band_min_weight=Decimal("0.01"), cash_band_max_weight=Decimal("0.05")
    )
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    results = RuleEngine.evaluate(state, strict_options, diag)
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
                weight=Decimal("0.55"),
                value=Money(amount=Decimal("550"), currency="SGD"),
            )
        ],
    )
    options = EngineOptions(single_position_max_weight=Decimal("0.50"))
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    results = RuleEngine.evaluate(state, options, diag)

    pos_rule = next(r for r in results if r.rule_id == "SINGLE_POSITION_MAX")
    assert pos_rule.status == "FAIL"
    assert pos_rule.severity == "HARD"
    assert pos_rule.measured == Decimal("0.55")


def test_no_shorting_fail():
    """Verifies strict no-shorting check in Rule Engine."""
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        positions=[
            PositionSummary(
                instrument_id="BAD_SHORT",
                quantity=Decimal("-10"),
                instrument_currency="USD",
                value_in_instrument_ccy=Money(amount=Decimal("-100"), currency="USD"),
                value_in_base_ccy=Money(amount=Decimal("-150"), currency="SGD"),
                weight=Decimal("-0.15"),
            )
        ],
    )

    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    results = RuleEngine.evaluate(state, EngineOptions(), diag)

    rule = next(r for r in results if r.rule_id == "NO_SHORTING")
    assert rule.status == "FAIL"
    assert rule.severity == "HARD"
    assert rule.measured == Decimal("-10")


def test_always_emit_all_rules():
    """RFC-0006B: All core rules must emit a result (PASS/FAIL)."""
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        allocation_by_asset_class=[],
        positions=[],
        cash_balances=[],
    )
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    results = RuleEngine.evaluate(state, EngineOptions(single_position_max_weight=None), diag)

    rule_ids = {r.rule_id for r in results}
    expected = {
        "CASH_BAND",
        "SINGLE_POSITION_MAX",
        "DATA_QUALITY",
        "MIN_TRADE_SIZE",
        "NO_SHORTING",
        "INSUFFICIENT_CASH",
    }
    assert expected.issubset(rule_ids)

    spm = next(r for r in results if r.rule_id == "SINGLE_POSITION_MAX")
    assert spm.status == "PASS"
    assert spm.reason_code == "NO_LIMIT_SET"


@pytest.mark.parametrize(
    "weight, expected_status",
    [
        (Decimal("0.5010"), "PASS"),
        (Decimal("0.5011"), "FAIL"),
    ],
)
def test_single_position_max_tolerance_boundary(weight, expected_status):
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        allocation_by_instrument=[
            AllocationMetric(
                key="EDGE_POS",
                weight=weight,
                value=Money(amount=Decimal("501"), currency="SGD"),
            )
        ],
    )
    diag = DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
    results = RuleEngine.evaluate(
        state,
        EngineOptions(single_position_max_weight=Decimal("0.50")),
        diag,
    )
    spm = next(r for r in results if r.rule_id == "SINGLE_POSITION_MAX")
    assert spm.status == expected_status


def test_min_trade_size_rule_reports_suppressed_intent_count():
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="SGD"),
        allocation_by_asset_class=[],
        positions=[],
    )
    diagnostics = DiagnosticsData(
        data_quality={},
        suppressed_intents=[
            {
                "instrument_id": "EQ_1",
                "reason": "MIN_NOTIONAL",
                "intended_notional": {"amount": "5", "currency": "SGD"},
                "threshold": {"amount": "10", "currency": "SGD"},
            },
            {
                "instrument_id": "EQ_2",
                "reason": "MIN_NOTIONAL",
                "intended_notional": {"amount": "6", "currency": "SGD"},
                "threshold": {"amount": "10", "currency": "SGD"},
            },
        ],
        warnings=[],
    )
    results = RuleEngine.evaluate(state, EngineOptions(), diagnostics)
    min_trade_size = next(result for result in results if result.rule_id == "MIN_TRADE_SIZE")
    assert min_trade_size.status == "PASS"
    assert min_trade_size.reason_code == "INTENTS_SUPPRESSED"
    assert min_trade_size.measured == Decimal("2")
