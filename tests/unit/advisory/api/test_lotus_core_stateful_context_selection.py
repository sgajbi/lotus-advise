from __future__ import annotations

from src.integrations.lotus_core.stateful_context import _held_position_instrument_ids


def test_held_position_instrument_ids_selects_unique_non_cash_security_ids() -> None:
    assert _held_position_instrument_ids(
        {
            "positions": [
                "bad-row",
                {"security_id": " CASH_USD ", "asset_class": " Cash "},
                {"security_id": " EQ_001 ", "asset_class": "Equity"},
                {"security_id": "EQ_001", "asset_class": "Equity"},
                {"security_id": "BOND_001", "asset_class": "Fixed Income"},
                {"security_id": "", "asset_class": "Equity"},
                {"asset_class": "Equity"},
            ]
        }
    ) == ["BOND_001", "EQ_001"]
