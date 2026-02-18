"""
FILE: tests/contracts/test_contract_models.py
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    GroupConstraint,
    Money,
    ShelfEntry,
    SimulatedState,
    TargetMethod,
)


def test_money_validation():
    m = Money(amount=Decimal("100.00"), currency="USD")
    assert m.amount == Decimal("100.00")
    assert m.currency == "USD"

    with pytest.raises(ValidationError):
        Money(amount="invalid", currency="USD")


def test_shelf_entry_status_validation():
    # Valid status
    s = ShelfEntry(instrument_id="AAPL", status="APPROVED")
    assert s.status == "APPROVED"

    # Invalid status
    with pytest.raises(ValidationError):
        ShelfEntry(instrument_id="AAPL", status="INVALID_STATUS")


def test_shelf_entry_attributes():
    # Test attribute tagging support (RFC-0008)
    s = ShelfEntry(
        instrument_id="AAPL",
        status="APPROVED",
        attributes={"sector": "TECH", "region": "US"},
    )
    assert s.attributes["sector"] == "TECH"
    assert s.attributes["region"] == "US"
    assert len(s.attributes) == 2


def test_simulated_state_structure():
    # Ensure compatibility with new allocation_by_attribute field
    state = SimulatedState(
        total_value=Money(amount=Decimal("100"), currency="USD"),
        positions=[],
        cash_balances=[],
        allocation_by_asset_class=[],
        allocation_by_instrument=[],
        allocation=[],
        allocation_by_attribute={"sector": []},
    )
    assert "sector" in state.allocation_by_attribute


def test_group_constraint_max_weight_bounds_validation():
    EngineOptions(group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.5"))})

    with pytest.raises(ValidationError):
        GroupConstraint(max_weight=Decimal("-0.01"))
    with pytest.raises(ValidationError):
        GroupConstraint(max_weight=Decimal("1.01"))


def test_group_constraint_key_format_validation():
    with pytest.raises(ValidationError):
        EngineOptions(group_constraints={"sectorTECH": GroupConstraint(max_weight=Decimal("0.5"))})
    with pytest.raises(ValidationError):
        EngineOptions(group_constraints={":TECH": GroupConstraint(max_weight=Decimal("0.5"))})
    with pytest.raises(ValidationError):
        EngineOptions(group_constraints={"sector:": GroupConstraint(max_weight=Decimal("0.5"))})


def test_diagnostics_supports_group_constraint_events():
    diag = DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        group_constraint_events=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )
    assert diag.group_constraint_events == []


def test_target_method_defaults_to_heuristic():
    options = EngineOptions()
    assert options.target_method == TargetMethod.HEURISTIC
