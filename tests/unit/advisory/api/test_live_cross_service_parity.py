from decimal import Decimal

from scripts.validate_cross_service_parity_live import (
    _security_trade_changes_from_proposal_body,
    _select_changed_state_security,
    _select_cross_currency_changed_state_security,
    _select_non_held_changed_state_security,
)


def test_select_changed_state_security_prefers_highest_weight_non_cash_position() -> None:
    positions = [
        {"security_id": "CASH_USD_BOOK_OPERATING", "asset_class": "Cash", "weight": "0.20"},
        {"security_id": "FO_BOND_LOW", "asset_class": "Fixed Income", "weight": "0.08"},
        {"security_id": "FO_FUND_HIGH", "asset_class": "Fund", "weight": "0.24"},
    ]

    selected = _select_changed_state_security(positions)

    assert selected == "FO_FUND_HIGH"


def test_security_trade_changes_from_proposal_body_preserves_trade_quantities_and_notional() -> (
    None
):
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
            "quantity": Decimal("1"),
            "amount": Decimal("101.35"),
            "currency": "USD",
            "metadata": {
                "proposal_intent_id": "oi_1",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        },
        {
            "security_id": "FO_BOND_SIEMENS_2031",
            "transaction_type": "SELL",
            "quantity": Decimal("2"),
            "metadata": {
                "proposal_intent_id": "oi_2",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        },
    ]


def test_select_cross_currency_changed_state_security_prefers_highest_weight_non_base_holding() -> (
    None
):
    positions = [
        {"security_id": "FO_USD", "asset_class": "Fund", "currency": "USD", "weight": "0.18"},
        {
            "security_id": "FO_EUR_LOW",
            "asset_class": "Bond",
            "currency": "EUR",
            "weight": "0.04",
        },
        {
            "security_id": "FO_EUR_HIGH",
            "asset_class": "Equity",
            "currency": "EUR",
            "weight": "0.16",
        },
        {"security_id": "CASH_EUR", "asset_class": "Cash", "currency": "EUR", "weight": "0.20"},
    ]

    selected = _select_cross_currency_changed_state_security(positions, base_currency="USD")

    assert selected == "FO_EUR_HIGH"


def test_select_non_held_changed_state_security_prefers_known_non_held_candidate() -> None:
    positions = [
        {"security_id": "FO_FUND_PIMCO_INC"},
        {"security_id": "FO_FUND_BLK_ALLOC"},
        {"security_id": "FO_BOND_UST_2030"},
    ]

    selected = _select_non_held_changed_state_security(
        positions,
        candidates=("FO_FUND_PIMCO_INC", "SEC_FUND_EM_EQ", "FO_BOND_UST_2030"),
    )

    assert selected == "SEC_FUND_EM_EQ"
