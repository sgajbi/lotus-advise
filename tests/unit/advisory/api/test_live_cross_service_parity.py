from scripts.validate_cross_service_parity_live import (
    _security_trade_changes_from_proposal_body,
    _select_changed_state_security,
)


def test_select_changed_state_security_prefers_highest_weight_non_cash_position() -> None:
    positions = [
        {"security_id": "CASH_USD_BOOK_OPERATING", "asset_class": "Cash", "weight": "0.20"},
        {"security_id": "FO_BOND_LOW", "asset_class": "Fixed Income", "weight": "0.08"},
        {"security_id": "FO_FUND_HIGH", "asset_class": "Fund", "weight": "0.24"},
    ]

    selected = _select_changed_state_security(positions)

    assert selected == "FO_FUND_HIGH"


def test_security_trade_changes_from_proposal_body_preserves_trade_quantities_and_notional(
) -> None:
    proposal_body = {
        "intents": [
            {
                "intent_type": "SECURITY_TRADE",
                "intent_id": "oi_1",
                "instrument_id": "FO_BOND_UST_2030",
                "side": "BUY",
                "quantity": "1",
                "notional": {"amount": "101.35", "currency": "USD"},
            },
            {
                "intent_type": "SECURITY_TRADE",
                "intent_id": "oi_2",
                "instrument_id": "FO_BOND_SIEMENS_2031",
                "side": "SELL",
                "quantity": "2",
            },
            {
                "intent_type": "CASH_FLOW",
                "intent_id": "oi_3",
            },
        ]
    }

    changes = _security_trade_changes_from_proposal_body(proposal_body)

    assert changes == [
        {
            "security_id": "FO_BOND_UST_2030",
            "transaction_type": "BUY",
            "quantity": 1.0,
            "amount": 101.35,
            "currency": "USD",
            "metadata": {
                "proposal_intent_id": "oi_1",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        },
        {
            "security_id": "FO_BOND_SIEMENS_2031",
            "transaction_type": "SELL",
            "quantity": 2.0,
            "metadata": {
                "proposal_intent_id": "oi_2",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        },
    ]
