from src.core.workspace.identifiers import (
    new_workspace_cash_flow_id,
    new_workspace_trade_id,
)
from src.core.workspace.models import (
    WorkspaceCashFlowDraft,
    WorkspaceDraftActionRequest,
    WorkspaceDraftState,
    WorkspaceTradeDraft,
)


class WorkspaceDraftActionError(ValueError):
    pass


def apply_workspace_draft_action_to_state(
    *,
    draft_state: WorkspaceDraftState,
    request: WorkspaceDraftActionRequest,
) -> None:
    if request.action_type == "ADD_TRADE":
        assert request.trade is not None
        draft_state.trade_drafts.append(
            WorkspaceTradeDraft(
                workspace_trade_id=new_workspace_trade_id(),
                trade=request.trade.model_copy(deep=True),
            )
        )
    elif request.action_type == "UPDATE_TRADE":
        assert request.trade is not None and request.workspace_trade_id is not None
        trade_draft = find_trade_draft(draft_state, request.workspace_trade_id)
        trade_draft.trade = request.trade.model_copy(deep=True)
    elif request.action_type == "REMOVE_TRADE":
        assert request.workspace_trade_id is not None
        remove_trade_draft(draft_state, request.workspace_trade_id)
    elif request.action_type == "ADD_CASH_FLOW":
        assert request.cash_flow is not None
        draft_state.cash_flow_drafts.append(
            WorkspaceCashFlowDraft(
                workspace_cash_flow_id=new_workspace_cash_flow_id(),
                cash_flow=request.cash_flow.model_copy(deep=True),
            )
        )
    elif request.action_type == "UPDATE_CASH_FLOW":
        assert request.cash_flow is not None and request.workspace_cash_flow_id is not None
        cash_flow_draft = find_cash_flow_draft(draft_state, request.workspace_cash_flow_id)
        cash_flow_draft.cash_flow = request.cash_flow.model_copy(deep=True)
    elif request.action_type == "REMOVE_CASH_FLOW":
        assert request.workspace_cash_flow_id is not None
        remove_cash_flow_draft(draft_state, request.workspace_cash_flow_id)
    elif request.action_type == "REPLACE_OPTIONS":
        assert request.options is not None
        draft_state.options = request.options.model_copy(deep=True)


def find_trade_draft(
    draft_state: WorkspaceDraftState,
    workspace_trade_id: str,
) -> WorkspaceTradeDraft:
    trade_draft = next(
        (
            item
            for item in draft_state.trade_drafts
            if item.workspace_trade_id == workspace_trade_id
        ),
        None,
    )
    if trade_draft is None:
        raise WorkspaceDraftActionError("WORKSPACE_TRADE_NOT_FOUND")
    return trade_draft


def find_cash_flow_draft(
    draft_state: WorkspaceDraftState,
    workspace_cash_flow_id: str,
) -> WorkspaceCashFlowDraft:
    cash_flow_draft = next(
        (
            item
            for item in draft_state.cash_flow_drafts
            if item.workspace_cash_flow_id == workspace_cash_flow_id
        ),
        None,
    )
    if cash_flow_draft is None:
        raise WorkspaceDraftActionError("WORKSPACE_CASH_FLOW_NOT_FOUND")
    return cash_flow_draft


def remove_trade_draft(
    draft_state: WorkspaceDraftState,
    workspace_trade_id: str,
) -> None:
    original_len = len(draft_state.trade_drafts)
    draft_state.trade_drafts = [
        item for item in draft_state.trade_drafts if item.workspace_trade_id != workspace_trade_id
    ]
    if len(draft_state.trade_drafts) == original_len:
        raise WorkspaceDraftActionError("WORKSPACE_TRADE_NOT_FOUND")


def remove_cash_flow_draft(
    draft_state: WorkspaceDraftState,
    workspace_cash_flow_id: str,
) -> None:
    original_len = len(draft_state.cash_flow_drafts)
    draft_state.cash_flow_drafts = [
        item
        for item in draft_state.cash_flow_drafts
        if item.workspace_cash_flow_id != workspace_cash_flow_id
    ]
    if len(draft_state.cash_flow_drafts) == original_len:
        raise WorkspaceDraftActionError("WORKSPACE_CASH_FLOW_NOT_FOUND")
