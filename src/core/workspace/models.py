from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.core.engine_options_models import EngineOptions
from src.core.proposal_request_models import (
    ProposedCashFlow,
    ProposedTrade,
)
from src.core.proposal_result_models import ProposalResult
from src.core.proposals.models import ProposalCreateResponse
from src.core.workspace import assistant_models as _assistant_models
from src.core.workspace.compare_models import (
    WorkspaceCompareDiffSummary as WorkspaceCompareDiffSummary,
)
from src.core.workspace.compare_models import (
    WorkspaceCompareRequest as WorkspaceCompareRequest,
)
from src.core.workspace.compare_models import (
    WorkspaceCompareResponse as WorkspaceCompareResponse,
)
from src.core.workspace.draft_models import (
    WorkspaceCashFlowDraft as WorkspaceCashFlowDraft,
)
from src.core.workspace.draft_models import (
    WorkspaceDraftState,
    WorkspaceEvaluationSummary,
)
from src.core.workspace.draft_models import (
    WorkspaceEvaluationImpactSummary as WorkspaceEvaluationImpactSummary,
)
from src.core.workspace.draft_models import (
    WorkspaceTradeDraft as WorkspaceTradeDraft,
)
from src.core.workspace.input_models import (
    WorkspaceInputMode,
    WorkspaceResolvedContext,
    WorkspaceStatefulInput,
    WorkspaceStatelessInput,
)
from src.core.workspace.version_models import (
    WorkspaceLifecycleLink,
    WorkspaceReplayEvidence,
    WorkspaceSavedVersion,
    WorkspaceSavedVersionSummary,
)

WorkspaceLifecycleState = Literal["ACTIVE", "PAUSED", "ARCHIVED"]
WorkspaceDraftActionType = Literal[
    "ADD_TRADE",
    "UPDATE_TRADE",
    "REMOVE_TRADE",
    "ADD_CASH_FLOW",
    "UPDATE_CASH_FLOW",
    "REMOVE_CASH_FLOW",
    "REPLACE_OPTIONS",
]

WorkspaceAssistantEvidence = _assistant_models.WorkspaceAssistantEvidence
WorkspaceAssistantRequest = _assistant_models.WorkspaceAssistantRequest
WorkspaceAssistantResponse = _assistant_models.WorkspaceAssistantResponse
WorkspaceAssistantWorkflowPackRun = _assistant_models.WorkspaceAssistantWorkflowPackRun
WorkspaceAssistantWorkflowPackRunFinding = (
    _assistant_models.WorkspaceAssistantWorkflowPackRunFinding
)
WorkspaceAssistantWorkflowPackRunReviewActionRequest = (
    _assistant_models.WorkspaceAssistantWorkflowPackRunReviewActionRequest
)
WorkspaceAssistantWorkflowPackRunReviewActionResponse = (
    _assistant_models.WorkspaceAssistantWorkflowPackRunReviewActionResponse
)


class WorkspaceSessionCreateRequest(BaseModel):
    workspace_name: str = Field(
        description="Advisor-facing workspace name used in Lotus advisory workflows.",
        examples=["Q2 2026 growth reallocation draft"],
    )
    created_by: str = Field(
        description="Actor identifier for the advisor or reviewer creating the workspace.",
        examples=["advisor_123"],
    )
    input_mode: WorkspaceInputMode = Field(
        description=(
            "Workspace input mode determining whether context is supplied directly or resolved "
            "upstream."
        ),
        examples=["stateful"],
    )
    stateless_input: Optional[WorkspaceStatelessInput] = Field(
        default=None,
        description="Direct advisory input payload for stateless workspace sessions.",
        examples=[
            {
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                        "base_currency": "USD",
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                }
            }
        ],
    )
    stateful_input: Optional[WorkspaceStatefulInput] = Field(
        default=None,
        description="Identifier-based input payload for stateful workspace sessions.",
        examples=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "household_id": "hh_001",
                "as_of": "2026-03-25",
                "mandate_id": "mandate_growth_01",
            }
        ],
    )

    @model_validator(mode="after")
    def validate_input_mode_payloads(self) -> "WorkspaceSessionCreateRequest":
        if self.input_mode == "stateless":
            if self.stateless_input is None or self.stateful_input is not None:
                raise ValueError(
                    "stateless workspaces require stateless_input and must not include "
                    "stateful_input"
                )
        if self.input_mode == "stateful":
            if self.stateful_input is None or self.stateless_input is not None:
                raise ValueError(
                    "stateful workspaces require stateful_input and must not include "
                    "stateless_input"
                )
        return self


class WorkspaceSession(BaseModel):
    workspace_id: str = Field(
        description="Workspace session identifier.",
        examples=["aws_001"],
    )
    workspace_name: str = Field(
        description="Advisor-facing workspace name.",
        examples=["Q2 2026 growth reallocation draft"],
    )
    lifecycle_state: WorkspaceLifecycleState = Field(
        description="Lifecycle state of the advisory workspace session.",
        examples=["ACTIVE"],
    )
    input_mode: WorkspaceInputMode = Field(
        description="Workspace input mode for this session.",
        examples=["stateful"],
    )
    created_by: str = Field(
        description="Actor identifier for the user that created the workspace.",
        examples=["advisor_123"],
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp of workspace creation.",
        examples=["2026-03-25T09:30:00+00:00"],
    )
    stateless_input: Optional[WorkspaceStatelessInput] = Field(
        default=None,
        description="Direct input payload for stateless workspaces.",
    )
    stateful_input: Optional[WorkspaceStatefulInput] = Field(
        default=None,
        description="Identifier-based input payload for stateful workspaces.",
    )
    draft_state: WorkspaceDraftState = Field(
        description="Current editable workspace draft state.",
    )
    resolved_context: Optional[WorkspaceResolvedContext] = Field(
        default=None,
        description="Resolved advisory context captured for replay and audit.",
    )
    evaluation_summary: Optional[WorkspaceEvaluationSummary] = Field(
        default=None,
        description="Current workspace evaluation summary for advisor and reviewer workflows.",
    )
    latest_proposal_result: Optional[ProposalResult] = Field(
        default=None,
        description="Optional latest full proposal result associated with the workspace draft.",
    )
    latest_replay_evidence: Optional[WorkspaceReplayEvidence] = Field(
        default=None,
        description="Latest replay-safe evidence captured for the current workspace draft.",
    )
    saved_version_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of saved workspace versions currently available for resume and compare "
            "workflows."
        ),
        examples=[2],
    )
    latest_saved_version: Optional[WorkspaceSavedVersionSummary] = Field(
        default=None,
        description="Latest saved workspace version summary, when one exists.",
    )
    lifecycle_link: Optional[WorkspaceLifecycleLink] = Field(
        default=None,
        description=(
            "Current persisted proposal lifecycle link, when the workspace has been handed off."
        ),
    )
    saved_versions: list[WorkspaceSavedVersion] = Field(
        default_factory=list,
        exclude=True,
        description="Internal saved workspace versions retained for resume and compare workflows.",
    )

    @model_validator(mode="after")
    def validate_session_mode_payloads(self) -> "WorkspaceSession":
        if self.input_mode == "stateless":
            if self.stateless_input is None or self.stateful_input is not None:
                raise ValueError(
                    "stateless workspace sessions require stateless_input and must not include "
                    "stateful_input"
                )
        if self.input_mode == "stateful":
            if self.stateful_input is None or self.stateless_input is not None:
                raise ValueError(
                    "stateful workspace sessions require stateful_input and must not include "
                    "stateless_input"
                )
        return self


class WorkspaceSessionCreateResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Created advisory workspace session.",
    )


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


class WorkspaceSaveRequest(BaseModel):
    saved_by: str = Field(
        description="Actor identifier saving the current workspace version.",
        examples=["advisor_123"],
    )
    version_label: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing label for the saved workspace version.",
        examples=["Initial sandbox draft"],
    )


class WorkspaceSaveResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Workspace session after the save operation.",
    )
    saved_version: WorkspaceSavedVersion = Field(
        description="Saved workspace version created by the request.",
    )


class WorkspaceSavedVersionListResponse(BaseModel):
    workspace_id: str = Field(
        description="Workspace session identifier.",
        examples=["aws_001"],
    )
    saved_versions: list[WorkspaceSavedVersion] = Field(
        description="Saved workspace versions available for compare and resume workflows.",
    )


class WorkspaceResumeRequest(BaseModel):
    actor_id: str = Field(
        description="Actor identifier resuming a saved workspace version.",
        examples=["advisor_123"],
    )
    workspace_version_id: str = Field(
        description="Saved workspace version identifier to restore into the current draft.",
        examples=["awv_001"],
    )


class WorkspaceLifecycleHandoffMetadata(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing proposal title to persist at first lifecycle handoff.",
        examples=["Q2 2026 growth reallocation proposal"],
    )
    advisor_notes: Optional[str] = Field(
        default=None,
        description="Optional advisor notes to persist at first lifecycle handoff.",
        examples=["Prepared after client review call with growth tilt preference."],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional jurisdiction code to persist at first lifecycle handoff.",
        examples=["SG"],
    )
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier to persist at first lifecycle handoff.",
        examples=["mandate_growth_01"],
    )


class WorkspaceLifecycleHandoffRequest(BaseModel):
    handoff_by: str = Field(
        description="Actor identifier performing the workspace-to-lifecycle handoff.",
        examples=["advisor_123"],
    )
    metadata: WorkspaceLifecycleHandoffMetadata = Field(
        default_factory=WorkspaceLifecycleHandoffMetadata,
        description=(
            "Optional persisted proposal metadata used when creating the first linked proposal."
        ),
    )


class WorkspaceLifecycleHandoffResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Workspace session after lifecycle handoff metadata is updated.",
    )
    handoff_action: Literal["CREATED_PROPOSAL", "CREATED_PROPOSAL_VERSION"] = Field(
        description="Lifecycle handoff action performed for the workspace.",
        examples=["CREATED_PROPOSAL"],
    )
    proposal: ProposalCreateResponse = Field(
        description=(
            "Persisted proposal lifecycle response payload returned by the proposal service."
        ),
    )
