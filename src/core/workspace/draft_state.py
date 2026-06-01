from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.workspace.draft_models import (
    WorkspaceCashFlowDraft,
    WorkspaceDraftState,
    WorkspaceTradeDraft,
)
from src.core.workspace.identifiers import (
    new_workspace_cash_flow_id,
    new_workspace_trade_id,
)


def build_draft_state_from_simulate_request(
    simulate_request: ProposalSimulateRequest,
) -> WorkspaceDraftState:
    return WorkspaceDraftState(
        options=simulate_request.options.model_copy(deep=True),
        alternatives_request=(
            simulate_request.alternatives_request.model_copy(deep=True)
            if simulate_request.alternatives_request is not None
            else None
        ),
        reference_model=(
            simulate_request.reference_model.model_copy(deep=True)
            if simulate_request.reference_model is not None
            else None
        ),
        trade_drafts=[
            WorkspaceTradeDraft(
                workspace_trade_id=new_workspace_trade_id(),
                trade=trade.model_copy(deep=True),
            )
            for trade in simulate_request.proposed_trades
        ],
        cash_flow_drafts=[
            WorkspaceCashFlowDraft(
                workspace_cash_flow_id=new_workspace_cash_flow_id(),
                cash_flow=cash_flow.model_copy(deep=True),
            )
            for cash_flow in simulate_request.proposed_cash_flows
        ],
    )


def apply_workspace_draft_state(
    *,
    base_request: ProposalSimulateRequest,
    draft_state: WorkspaceDraftState,
) -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot=base_request.portfolio_snapshot.model_copy(deep=True),
        market_data_snapshot=base_request.market_data_snapshot.model_copy(deep=True),
        shelf_entries=[entry.model_copy(deep=True) for entry in base_request.shelf_entries],
        options=draft_state.options.model_copy(deep=True),
        proposed_cash_flows=[
            draft.cash_flow.model_copy(deep=True) for draft in draft_state.cash_flow_drafts
        ],
        proposed_trades=[draft.trade.model_copy(deep=True) for draft in draft_state.trade_drafts],
        reference_model=(
            draft_state.reference_model.model_copy(deep=True)
            if draft_state.reference_model is not None
            else None
        ),
        alternatives_request=(
            draft_state.alternatives_request.model_copy(deep=True)
            if draft_state.alternatives_request is not None
            else None
        ),
    )
