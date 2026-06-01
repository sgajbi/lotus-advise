from src.core.proposal_request_models import ProposedCashFlow, ProposedTrade
from src.core.workspace.draft_models import (
    WorkspaceCashFlowDraft,
    WorkspaceDraftState,
    WorkspaceTradeDraft,
)
from src.core.workspace.identifiers import (
    new_workspace_cash_flow_id,
    new_workspace_trade_id,
)
from src.core.workspace.models import WorkspaceDraftActionRequest


class WorkspaceDraftActionError(ValueError):
    pass


def _require_trade(request: WorkspaceDraftActionRequest) -> ProposedTrade:
    if request.trade is None:
        raise WorkspaceDraftActionError("WORKSPACE_DRAFT_TRADE_REQUIRED")
    return request.trade


def _require_cash_flow(request: WorkspaceDraftActionRequest) -> ProposedCashFlow:
    if request.cash_flow is None:
        raise WorkspaceDraftActionError("WORKSPACE_DRAFT_CASH_FLOW_REQUIRED")
    return request.cash_flow


def _require_workspace_trade_id(request: WorkspaceDraftActionRequest) -> str:
    if request.workspace_trade_id is None:
        raise WorkspaceDraftActionError("WORKSPACE_TRADE_ID_REQUIRED")
    return request.workspace_trade_id


def _require_workspace_cash_flow_id(request: WorkspaceDraftActionRequest) -> str:
    if request.workspace_cash_flow_id is None:
        raise WorkspaceDraftActionError("WORKSPACE_CASH_FLOW_ID_REQUIRED")
    return request.workspace_cash_flow_id


def apply_workspace_draft_action_to_state(
    *,
    draft_state: WorkspaceDraftState,
    request: WorkspaceDraftActionRequest,
) -> None:
    if request.action_type == "ADD_TRADE":
        draft_state.trade_drafts.append(
            WorkspaceTradeDraft(
                workspace_trade_id=new_workspace_trade_id(),
                trade=_require_trade(request).model_copy(deep=True),
            )
        )
    elif request.action_type == "UPDATE_TRADE":
        trade_draft = find_trade_draft(draft_state, _require_workspace_trade_id(request))
        trade_draft.trade = _require_trade(request).model_copy(deep=True)
    elif request.action_type == "REMOVE_TRADE":
        remove_trade_draft(draft_state, _require_workspace_trade_id(request))
    elif request.action_type == "ADD_CASH_FLOW":
        draft_state.cash_flow_drafts.append(
            WorkspaceCashFlowDraft(
                workspace_cash_flow_id=new_workspace_cash_flow_id(),
                cash_flow=_require_cash_flow(request).model_copy(deep=True),
            )
        )
    elif request.action_type == "UPDATE_CASH_FLOW":
        cash_flow_draft = find_cash_flow_draft(
            draft_state,
            _require_workspace_cash_flow_id(request),
        )
        cash_flow_draft.cash_flow = _require_cash_flow(request).model_copy(deep=True)
    elif request.action_type == "REMOVE_CASH_FLOW":
        remove_cash_flow_draft(draft_state, _require_workspace_cash_flow_id(request))
    elif request.action_type == "REPLACE_OPTIONS":
        if request.options is None:
            raise WorkspaceDraftActionError("WORKSPACE_DRAFT_OPTIONS_REQUIRED")
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
