from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.core.engine_options_models import EngineOptions
from src.core.proposal_request_models import ProposedCashFlow, ProposedTrade
from src.core.workspace.session_models import WorkspaceSession

WorkspaceDraftActionType = Literal[
    "ADD_TRADE",
    "UPDATE_TRADE",
    "REMOVE_TRADE",
    "ADD_CASH_FLOW",
    "UPDATE_CASH_FLOW",
    "REMOVE_CASH_FLOW",
    "REPLACE_OPTIONS",
]

TRADE_DRAFT_ACTIONS = {"ADD_TRADE", "UPDATE_TRADE", "REMOVE_TRADE"}
CASH_FLOW_DRAFT_ACTIONS = {"ADD_CASH_FLOW", "UPDATE_CASH_FLOW", "REMOVE_CASH_FLOW"}


class WorkspaceDraftActionRequest(BaseModel):
    actor_id: str = Field(
        description="Actor identifier applying the workspace draft action.",
        examples=["advisor_123"],
    )
    action_type: WorkspaceDraftActionType = Field(
        description="Workspace draft action to apply.",
        examples=["ADD_TRADE"],
    )
    workspace_trade_id: Optional[str] = Field(
        default=None,
        description="Workspace trade identifier used by trade update and remove actions.",
        examples=["wtd_001"],
    )
    workspace_cash_flow_id: Optional[str] = Field(
        default=None,
        description="Workspace cash-flow identifier used by cash-flow update and remove actions.",
        examples=["wcf_001"],
    )
    trade: Optional[ProposedTrade] = Field(
        default=None,
        description="Trade payload used by add or update trade actions.",
    )
    cash_flow: Optional[ProposedCashFlow] = Field(
        default=None,
        description="Cash-flow payload used by add or update cash-flow actions.",
    )
    options: Optional[EngineOptions] = Field(
        default=None,
        description="Replacement workspace options payload used by REPLACE_OPTIONS.",
    )

    @model_validator(mode="after")
    def validate_action_payload(self) -> "WorkspaceDraftActionRequest":
        _validate_required_trade_payload(self)
        _validate_required_cash_flow_payload(self)
        _validate_required_options_payload(self)
        _validate_action_identifier_scope(self)
        return self


def _validate_required_trade_payload(request: WorkspaceDraftActionRequest) -> None:
    if request.action_type == "ADD_TRADE" and request.trade is None:
        raise ValueError("ADD_TRADE requires trade")
    if request.action_type == "UPDATE_TRADE":
        if request.trade is None or request.workspace_trade_id is None:
            raise ValueError("UPDATE_TRADE requires workspace_trade_id and trade")
    if request.action_type == "REMOVE_TRADE" and request.workspace_trade_id is None:
        raise ValueError("REMOVE_TRADE requires workspace_trade_id")


def _validate_required_cash_flow_payload(request: WorkspaceDraftActionRequest) -> None:
    if request.action_type == "ADD_CASH_FLOW" and request.cash_flow is None:
        raise ValueError("ADD_CASH_FLOW requires cash_flow")
    if request.action_type == "UPDATE_CASH_FLOW":
        if request.cash_flow is None or request.workspace_cash_flow_id is None:
            raise ValueError("UPDATE_CASH_FLOW requires workspace_cash_flow_id and cash_flow")
    if request.action_type == "REMOVE_CASH_FLOW" and request.workspace_cash_flow_id is None:
        raise ValueError("REMOVE_CASH_FLOW requires workspace_cash_flow_id")


def _validate_required_options_payload(request: WorkspaceDraftActionRequest) -> None:
    if request.action_type == "REPLACE_OPTIONS" and request.options is None:
        raise ValueError("REPLACE_OPTIONS requires options")


def _validate_action_identifier_scope(request: WorkspaceDraftActionRequest) -> None:
    if request.action_type not in TRADE_DRAFT_ACTIONS and request.workspace_trade_id is not None:
        raise ValueError("workspace_trade_id is only valid for trade actions")
    if (
        request.action_type not in CASH_FLOW_DRAFT_ACTIONS
        and request.workspace_cash_flow_id is not None
    ):
        raise ValueError("workspace_cash_flow_id is only valid for cash-flow actions")


class WorkspaceDraftActionResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Workspace session after the draft action and optional re-evaluation.",
    )
