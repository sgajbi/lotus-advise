from __future__ import annotations

from decimal import Decimal

from src.core.models import Money, Position
from src.integrations.lotus_core.stateful_context import _build_positions


def test_stateful_build_positions_maps_valid_valuation_to_base_currency() -> None:
    positions_payload = {
        "positions": [
            {
                "security_id": " EQ_US_001 ",
                "asset_class": "Equity",
                "quantity": "12.5",
                "valuation": {"market_value": "1050.25"},
            },
            {
                "security_id": "CASH_USD",
                "asset_class": "Cash",
                "quantity": "1000",
                "valuation": {"market_value": "1000"},
            },
            {
                "security_id": "SEC_MISSING_VALUE",
                "asset_class": "Bond",
                "quantity": "3",
                "valuation": {"market_price": "99.5"},
            },
        ]
    }

    positions = _build_positions(positions_payload, portfolio_base_currency="SGD")

    assert positions == [
        Position(
            instrument_id="EQ_US_001",
            quantity=Decimal("12.5"),
            market_value=Money(amount=Decimal("1050.25"), currency="SGD"),
            lots=[],
        ),
        Position(
            instrument_id="SEC_MISSING_VALUE",
            quantity=Decimal("3"),
            market_value=None,
            lots=[],
        ),
    ]
