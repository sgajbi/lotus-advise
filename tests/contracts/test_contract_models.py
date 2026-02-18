"""
FILE: tests/contracts/test_contract_models.py
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    Money,
    ShelfEntry,
    SimulatedState,
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
