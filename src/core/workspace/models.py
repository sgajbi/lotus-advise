from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.core.models import (
    EngineOptions,
    GateDecision,
    ProposalResult,
    ProposalSimulateRequest,
    ProposedCashFlow,
    ProposedTrade,
    ReferenceModel,
)
from src.core.proposals.models import ProposalCreateResponse

WorkspaceInputMode = Literal["stateless", "stateful"]
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


class WorkspaceStatelessInput(BaseModel):
    simulate_request: ProposalSimulateRequest = Field(
        description=(
            "Full advisory simulation payload supplied directly by the caller for sandbox, replay, "
            "or external integration workflows."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "250000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )


class WorkspaceStatefulInput(BaseModel):
    portfolio_id: str = Field(
        description="Canonical Lotus portfolio identifier resolved through upstream services.",
        examples=["pf_advisory_01"],
    )
    as_of: str = Field(
        description="Business date or timestamp used to resolve the source portfolio context.",
        examples=["2026-03-25"],
    )
    household_id: Optional[str] = Field(
        default=None,
        description="Optional household identifier when the advisory workflow is household-scoped.",
        examples=["hh_001"],
    )
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier used to enrich the advisory context.",
        examples=["mandate_growth_01"],
    )
    benchmark_id: Optional[str] = Field(
        default=None,
        description="Optional benchmark identifier for context-aware evaluation and comparison.",
        examples=["benchmark_balanced_usd"],
    )


class WorkspaceResolvedContext(BaseModel):
    portfolio_id: str = Field(
        description="Resolved portfolio identifier used by the workspace evaluation.",
        examples=["pf_advisory_01"],
    )
    as_of: str = Field(
        description="Resolved business date or timestamp used during evaluation.",
        examples=["2026-03-25"],
    )
    portfolio_snapshot_id: Optional[str] = Field(
        default=None,
        description="Upstream portfolio snapshot identifier captured for replay and audit.",
        examples=["ps_20260325_001"],
    )
    market_data_snapshot_id: Optional[str] = Field(
        default=None,
        description="Upstream market-data snapshot identifier captured for replay and audit.",
        examples=["md_20260325_001"],
    )
    risk_context_id: Optional[str] = Field(
        default=None,
        description="Optional upstream risk-context identifier used for advisory enrichment.",
        examples=["risk_ctx_001"],
    )
    reporting_context_id: Optional[str] = Field(
        default=None,
        description="Optional reporting-context identifier used to correlate downstream report generation.",
        examples=["report_ctx_001"],
    )


class WorkspaceTradeDraft(BaseModel):
    workspace_trade_id: str = Field(
        description="Workspace-local trade identifier used for deterministic draft editing.",
        examples=["wtd_001"],
    )
    trade: ProposedTrade = Field(
        description="Advisor-entered trade currently included in the workspace draft.",
    )


class WorkspaceCashFlowDraft(BaseModel):
    workspace_cash_flow_id: str = Field(
        description="Workspace-local cash-flow identifier used for deterministic draft editing.",
        examples=["wcf_001"],
    )
    cash_flow: ProposedCashFlow = Field(
        description="Advisor-entered cash-flow currently included in the workspace draft.",
    )


class WorkspaceDraftState(BaseModel):
    options: EngineOptions = Field(
        default_factory=EngineOptions,
        description="Current workspace-level evaluation options.",
    )
    reference_model: Optional[ReferenceModel] = Field(
        default=None,
        description="Optional reference model currently attached to the workspace draft.",
    )
    trade_drafts: list[WorkspaceTradeDraft] = Field(
        default_factory=list,
        description="Current ordered trade draft items in the workspace.",
    )
    cash_flow_drafts: list[WorkspaceCashFlowDraft] = Field(
        default_factory=list,
        description="Current ordered cash-flow draft items in the workspace.",
    )


class WorkspaceEvaluationImpactSummary(BaseModel):
    portfolio_value_delta_base_ccy: str = Field(
        description="Formatted base-currency delta between source portfolio value and current draft evaluation.",
        examples=["-1250.50"],
    )
    trade_count: int = Field(
        description="Number of current draft trades in the workspace.",
        examples=[3],
    )
    cash_flow_count: int = Field(
        description="Number of current draft cash-flow actions in the workspace.",
        examples=[1],
    )


class WorkspaceEvaluationSummary(BaseModel):
    status: Literal["READY", "PENDING_REVIEW", "BLOCKED"] = Field(
        description="Top-level advisory workflow posture for the current workspace draft.",
        examples=["PENDING_REVIEW"],
    )
    gate_decision: Optional[GateDecision] = Field(
        default=None,
        description="Optional gate decision derived from the current draft evaluation.",
    )
    blocking_issue_count: int = Field(
        default=0,
        ge=0,
        description="Count of blocking issues that currently prevent workflow progression.",
        examples=[1],
    )
    review_issue_count: int = Field(
        default=0,
        ge=0,
        description="Count of review issues that currently require human review but do not block evaluation.",
        examples=[2],
    )
    impact_summary: WorkspaceEvaluationImpactSummary = Field(
        description="Compact portfolio-impact summary for workspace cards and list views.",
        examples=[
            {
                "portfolio_value_delta_base_ccy": "-1250.50",
                "trade_count": 3,
                "cash_flow_count": 1,
            }
        ],
    )


class WorkspaceReplayEvidence(BaseModel):
    input_mode: WorkspaceInputMode = Field(
        description="Workspace input mode used when the draft state was evaluated or saved.",
        examples=["stateless"],
    )
    resolved_context: Optional[WorkspaceResolvedContext] = Field(
        default=None,
        description="Resolved advisory context captured for audit and replay.",
    )
    draft_state_hash: str = Field(
        description="Canonical hash of the saved workspace draft state.",
        examples=["7f4fb61c1be6f12ab57f0b145fbe590710f535d79418a8f1ca5c9542e6d23813"],
    )
    evaluation_request_hash: Optional[str] = Field(
        default=None,
        description="Canonical hash of the simulation request used for the latest deterministic evaluation.",
        examples=["2fd1f3c2ecde4e86fbeb5dff19df8fd5b4b9e24473e7a17f80f4d3d57f644ca8"],
    )
    captured_at: str = Field(
        description="UTC ISO8601 timestamp when replay evidence was captured.",
        examples=["2026-03-25T09:45:00+00:00"],
    )


class WorkspaceSavedVersionSummary(BaseModel):
    workspace_version_id: str = Field(
        description="Saved workspace version identifier.",
        examples=["awv_001"],
    )
    version_number: int = Field(
        description="Monotonic saved version number for the workspace session.",
        examples=[1],
    )
    version_label: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing label for the saved version.",
        examples=["Initial sandbox draft"],
    )
    saved_by: str = Field(
        description="Actor identifier that saved the workspace version.",
        examples=["advisor_123"],
    )
    saved_at: str = Field(
        description="UTC ISO8601 timestamp when the workspace version was saved.",
        examples=["2026-03-25T09:45:00+00:00"],
    )


class WorkspaceSavedVersion(BaseModel):
    workspace_version_id: str = Field(
        description="Saved workspace version identifier.",
        examples=["awv_001"],
    )
    version_number: int = Field(
        description="Monotonic saved version number for the workspace session.",
        examples=[1],
    )
    version_label: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing label for the saved version.",
        examples=["Initial sandbox draft"],
    )
    saved_by: str = Field(
        description="Actor identifier that saved the workspace version.",
        examples=["advisor_123"],
    )
    saved_at: str = Field(
        description="UTC ISO8601 timestamp when the workspace version was saved.",
        examples=["2026-03-25T09:45:00+00:00"],
    )
    draft_state: WorkspaceDraftState = Field(
        description="Saved draft state for replay, resume, and compare workflows.",
    )
    evaluation_summary: Optional[WorkspaceEvaluationSummary] = Field(
        default=None,
        description="Saved evaluation summary associated with the version.",
    )
    latest_proposal_result: Optional[ProposalResult] = Field(
        default=None,
        description="Optional full proposal result associated with the saved version.",
    )
    replay_evidence: WorkspaceReplayEvidence = Field(
        description="Replay-safe evidence bundle captured for the saved version.",
    )


class WorkspaceLifecycleLink(BaseModel):
    proposal_id: str = Field(
        description="Persisted advisory proposal identifier linked to the workspace.",
        examples=["pp_001"],
    )
    current_version_no: int = Field(
        description="Latest persisted proposal version number created from this workspace.",
        examples=[1],
    )
    last_handoff_at: str = Field(
        description="UTC ISO8601 timestamp of the latest workspace-to-lifecycle handoff.",
        examples=["2026-03-25T10:00:00+00:00"],
    )
    last_handoff_by: str = Field(
        description="Actor identifier that performed the latest workspace-to-lifecycle handoff.",
        examples=["advisor_123"],
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
        description="Workspace input mode determining whether context is supplied directly or resolved upstream.",
        examples=["stateful"],
    )
    stateless_input: Optional[WorkspaceStatelessInput] = Field(
        default=None,
        description="Direct advisory input payload for stateless workspace sessions.",
        examples=[
            {
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_advisory_01",
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
                "portfolio_id": "pf_advisory_01",
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
                    "stateless workspaces require stateless_input and must not include stateful_input"
                )
        if self.input_mode == "stateful":
            if self.stateful_input is None or self.stateless_input is not None:
                raise ValueError(
                    "stateful workspaces require stateful_input and must not include stateless_input"
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
        description="Number of saved workspace versions currently available for resume and compare workflows.",
        examples=[2],
    )
    latest_saved_version: Optional[WorkspaceSavedVersionSummary] = Field(
        default=None,
        description="Latest saved workspace version summary, when one exists.",
    )
    lifecycle_link: Optional[WorkspaceLifecycleLink] = Field(
        default=None,
        description="Current persisted proposal lifecycle link, when the workspace has been handed off.",
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
                    "stateless workspace sessions require stateless_input and must not include stateful_input"
                )
        if self.input_mode == "stateful":
            if self.stateful_input is None or self.stateless_input is not None:
                raise ValueError(
                    "stateful workspace sessions require stateful_input and must not include stateless_input"
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


class WorkspaceCompareRequest(BaseModel):
    workspace_version_id: str = Field(
        description="Saved workspace version identifier used as the comparison baseline.",
        examples=["awv_001"],
    )


class WorkspaceCompareDiffSummary(BaseModel):
    trade_count_delta: int = Field(
        description="Current draft trade count minus the baseline saved version trade count.",
        examples=[1],
    )
    cash_flow_count_delta: int = Field(
        description="Current draft cash-flow count minus the baseline saved version cash-flow count.",
        examples=[-1],
    )
    options_changed: bool = Field(
        description="Whether the current workspace options differ from the baseline saved version.",
        examples=[True],
    )
    reference_model_changed: bool = Field(
        description="Whether the current reference model differs from the baseline saved version.",
        examples=[False],
    )
    evaluation_status_changed: bool = Field(
        description="Whether the current evaluation status differs from the baseline saved version.",
        examples=[True],
    )


class WorkspaceCompareResponse(BaseModel):
    workspace_id: str = Field(
        description="Workspace session identifier.",
        examples=["aws_001"],
    )
    baseline_version: WorkspaceSavedVersion = Field(
        description="Saved workspace version used as the comparison baseline.",
    )
    current_evaluation_summary: Optional[WorkspaceEvaluationSummary] = Field(
        default=None,
        description="Current evaluation summary for the active workspace draft.",
    )
    current_replay_evidence: Optional[WorkspaceReplayEvidence] = Field(
        default=None,
        description="Current replay evidence for the active workspace draft.",
    )
    diff_summary: WorkspaceCompareDiffSummary = Field(
        description="Deterministic comparison summary between the current draft and the baseline version.",
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
        description="Optional persisted proposal metadata used when creating the first linked proposal.",
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
        description="Persisted proposal lifecycle response payload returned by the proposal service.",
    )
