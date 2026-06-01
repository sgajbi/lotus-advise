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
        trade_actions = {"ADD_TRADE", "UPDATE_TRADE", "REMOVE_TRADE"}
        cash_flow_actions = {"ADD_CASH_FLOW", "UPDATE_CASH_FLOW", "REMOVE_CASH_FLOW"}
        if self.action_type == "ADD_TRADE" and self.trade is None:
            raise ValueError("ADD_TRADE requires trade")
        if self.action_type == "UPDATE_TRADE":
            if self.trade is None or self.workspace_trade_id is None:
                raise ValueError("UPDATE_TRADE requires workspace_trade_id and trade")
        if self.action_type == "REMOVE_TRADE" and self.workspace_trade_id is None:
            raise ValueError("REMOVE_TRADE requires workspace_trade_id")
        if self.action_type == "ADD_CASH_FLOW" and self.cash_flow is None:
            raise ValueError("ADD_CASH_FLOW requires cash_flow")
        if self.action_type == "UPDATE_CASH_FLOW":
            if self.cash_flow is None or self.workspace_cash_flow_id is None:
                raise ValueError("UPDATE_CASH_FLOW requires workspace_cash_flow_id and cash_flow")
        if self.action_type == "REMOVE_CASH_FLOW" and self.workspace_cash_flow_id is None:
            raise ValueError("REMOVE_CASH_FLOW requires workspace_cash_flow_id")
        if self.action_type == "REPLACE_OPTIONS" and self.options is None:
            raise ValueError("REPLACE_OPTIONS requires options")
        if self.action_type not in trade_actions and self.workspace_trade_id is not None:
            raise ValueError("workspace_trade_id is only valid for trade actions")
        if self.action_type not in cash_flow_actions and self.workspace_cash_flow_id is not None:
            raise ValueError("workspace_cash_flow_id is only valid for cash-flow actions")
        return self


class WorkspaceDraftActionResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Workspace session after the draft action and optional re-evaluation.",
    )
