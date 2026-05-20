from decimal import Decimal

import pytest

from src.core.workspace.draft_actions import (
    WorkspaceDraftActionError,
    apply_workspace_draft_action_to_state,
)
from src.core.workspace.models import WorkspaceDraftActionRequest, WorkspaceDraftState


def test_apply_workspace_draft_action_adds_updates_and_removes_trade():
    draft_state = WorkspaceDraftState()
    add_request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "ADD_TRADE",
            "trade": {"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"},
        }
    )
    apply_workspace_draft_action_to_state(draft_state=draft_state, request=add_request)

    trade_id = draft_state.trade_drafts[0].workspace_trade_id
    assert trade_id.startswith("wtd_")
    update_request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "UPDATE_TRADE",
            "workspace_trade_id": trade_id,
            "trade": {"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "3"},
        }
    )
    apply_workspace_draft_action_to_state(draft_state=draft_state, request=update_request)
    assert draft_state.trade_drafts[0].trade.quantity == Decimal("3")

    remove_request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "REMOVE_TRADE",
            "workspace_trade_id": trade_id,
        }
    )
    apply_workspace_draft_action_to_state(draft_state=draft_state, request=remove_request)
    assert draft_state.trade_drafts == []


def test_apply_workspace_draft_action_adds_updates_and_removes_cash_flow():
    draft_state = WorkspaceDraftState()
    add_request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "ADD_CASH_FLOW",
            "cash_flow": {"currency": "USD", "amount": "250"},
        }
    )
    apply_workspace_draft_action_to_state(draft_state=draft_state, request=add_request)

    cash_flow_id = draft_state.cash_flow_drafts[0].workspace_cash_flow_id
    assert cash_flow_id.startswith("wcf_")
    update_request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "UPDATE_CASH_FLOW",
            "workspace_cash_flow_id": cash_flow_id,
            "cash_flow": {"currency": "USD", "amount": "300"},
        }
    )
    apply_workspace_draft_action_to_state(draft_state=draft_state, request=update_request)
    assert draft_state.cash_flow_drafts[0].cash_flow.amount == Decimal("300")

    remove_request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "REMOVE_CASH_FLOW",
            "workspace_cash_flow_id": cash_flow_id,
        }
    )
    apply_workspace_draft_action_to_state(draft_state=draft_state, request=remove_request)
    assert draft_state.cash_flow_drafts == []


def test_apply_workspace_draft_action_reports_missing_rows():
    draft_state = WorkspaceDraftState()
    request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "REMOVE_TRADE",
            "workspace_trade_id": "wtd_missing",
        }
    )

    with pytest.raises(WorkspaceDraftActionError) as exc:
        apply_workspace_draft_action_to_state(draft_state=draft_state, request=request)

    assert str(exc.value) == "WORKSPACE_TRADE_NOT_FOUND"
