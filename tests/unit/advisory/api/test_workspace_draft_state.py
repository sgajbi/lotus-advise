from decimal import Decimal

from src.core.models import ProposalSimulateRequest
from src.core.workspace.draft_state import (
    apply_workspace_draft_state,
    build_draft_state_from_simulate_request,
)


def _simulate_request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "pf_draft",
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {"prices": [], "fx_rates": []},
            "shelf_entries": [],
            "options": {"enable_proposal_simulation": True, "auto_funding": False},
            "proposed_cash_flows": [{"currency": "USD", "amount": "250"}],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
        }
    )


def test_build_draft_state_from_simulate_request_preserves_editable_rows():
    draft_state = build_draft_state_from_simulate_request(_simulate_request())

    assert draft_state.trade_drafts[0].workspace_trade_id.startswith("wtd_")
    assert draft_state.trade_drafts[0].trade.instrument_id == "EQ_NEW"
    assert draft_state.cash_flow_drafts[0].workspace_cash_flow_id.startswith("wcf_")
    assert draft_state.cash_flow_drafts[0].cash_flow.amount == Decimal("250")
    assert draft_state.options.auto_funding is False


def test_apply_workspace_draft_state_rebuilds_simulation_request_from_drafts():
    base_request = _simulate_request()
    draft_state = build_draft_state_from_simulate_request(base_request)
    draft_state.trade_drafts.clear()

    rebuilt = apply_workspace_draft_state(
        base_request=base_request,
        draft_state=draft_state,
    )

    assert rebuilt.proposed_trades == []
    assert len(rebuilt.proposed_cash_flows) == 1
    assert rebuilt.options.auto_funding is False
