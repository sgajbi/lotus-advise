from typing import Literal, Optional, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.common.actors import normalize_required_actor_id
from src.core.engine_options_models import EngineOptions
from src.core.proposal_request_models import (
    ProposedCashFlow,
    ProposedTrade,
)
from src.core.proposal_result_models import ProposalResult
from src.core.proposals.models import ProposalCreateResponse
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
WorkspaceAssistantWorkflowPackRunReviewActionType = Literal[
    "ACCEPT",
    "REJECT",
    "REVISE",
    "SUPERSEDE",
    "ABANDON",
]
_WORKSPACE_ASSISTANT_ACTOR_ID_MAX_LENGTH = 128
_WORKSPACE_ASSISTANT_INSTRUCTION_MAX_LENGTH = 1000
_WORKSPACE_ASSISTANT_RUN_ID_MAX_LENGTH = 160
_WORKSPACE_ASSISTANT_REVIEW_REASON_MAX_LENGTH = 1000


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
        description=(
            "Current draft cash-flow count minus the baseline saved version cash-flow count."
        ),
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
        description=(
            "Whether the current evaluation status differs from the baseline saved version."
        ),
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
        description=(
            "Deterministic comparison summary between the current draft and the baseline version."
        ),
    )


class WorkspaceAssistantRequest(BaseModel):
    requested_by: str = Field(
        description="Actor identifier requesting the advisory AI assistance output.",
        examples=["advisor_123"],
        max_length=_WORKSPACE_ASSISTANT_ACTOR_ID_MAX_LENGTH,
    )
    instruction: str = Field(
        description="Advisor instruction for the evidence-grounded workspace rationale request.",
        examples=["Summarize the proposal rationale for an advisor review note."],
        min_length=1,
        max_length=_WORKSPACE_ASSISTANT_INSTRUCTION_MAX_LENGTH,
    )

    @field_validator("requested_by")
    @classmethod
    def _normalize_requested_by(cls, value: str) -> str:
        normalized = normalize_required_actor_id(
            value,
            error_code="WORKSPACE_ASSISTANT_ACTOR_REQUIRED",
        )
        if len(normalized) > _WORKSPACE_ASSISTANT_ACTOR_ID_MAX_LENGTH:
            raise ValueError("WORKSPACE_ASSISTANT_ACTOR_TOO_LONG")
        return cast(str, normalized)

    @field_validator("instruction")
    @classmethod
    def _normalize_instruction(cls, value: str) -> str:
        normalized = _normalize_workspace_assistant_text(
            value,
            error_code="WORKSPACE_ASSISTANT_INSTRUCTION_REQUIRED",
        )
        if len(normalized) > _WORKSPACE_ASSISTANT_INSTRUCTION_MAX_LENGTH:
            raise ValueError("WORKSPACE_ASSISTANT_INSTRUCTION_TOO_LONG")
        return cast(str, normalized)


class WorkspaceAssistantEvidence(BaseModel):
    workspace_id: str = Field(
        description="Workspace session identifier used to build the AI evidence bundle.",
        examples=["aws_001"],
    )
    input_mode: WorkspaceInputMode = Field(
        description="Workspace input mode for the evaluated advisory draft.",
        examples=["stateful"],
    )
    resolved_context: Optional[WorkspaceResolvedContext] = Field(
        default=None,
        description="Resolved advisory context attached to the evaluated workspace.",
    )
    evaluation_summary: WorkspaceEvaluationSummary = Field(
        description="Current deterministic evaluation summary supplied to the AI assist boundary.",
    )
    proposal_status: str = Field(
        description="Current deterministic proposal status from the evaluated workspace result.",
        examples=["READY"],
    )


class WorkspaceAssistantWorkflowPackRunFinding(BaseModel):
    finding_id: str = Field(
        description="Stable workflow-pack supportability finding identifier.",
        examples=["review_pending"],
    )
    severity: str = Field(
        description="Workflow-pack supportability severity emitted by lotus-ai.",
        examples=["ACTION_REQUIRED"],
    )
    summary: str = Field(
        description="Short workflow-pack supportability summary.",
        examples=["Run is awaiting review."],
    )


class WorkspaceAssistantWorkflowPackRun(BaseModel):
    run_id: str = Field(
        description=(
            "Stable lotus-ai workflow-pack run identifier backing this workspace rationale."
        ),
        examples=["packrun_workspace_rationale_req_001"],
    )
    runtime_state: str = Field(
        description="Current lotus-ai runtime state for the workflow-pack run.",
        examples=["COMPLETED"],
    )
    review_state: str = Field(
        description="Current lotus-ai review state for the workflow-pack run.",
        examples=["AWAITING_REVIEW"],
    )
    allowed_review_actions: list[str] = Field(
        default_factory=list,
        description=(
            "Bounded lotus-ai review actions currently accepted by the workflow-pack ledger."
        ),
        examples=[["ACCEPT", "REJECT", "REVISE"]],
    )
    supportability_status: str = Field(
        description="Current lotus-ai supportability posture for the workflow-pack run.",
        examples=["ACTION_REQUIRED"],
    )
    review_pending: bool = Field(
        description="Whether lotus-ai still reports the workflow-pack run as pending review.",
    )
    superseded: bool = Field(
        description=(
            "Whether lotus-ai marks the workflow-pack run as historical due to replacement lineage."
        ),
    )
    workflow_authority_owner: str = Field(
        description=(
            "Service boundary retaining consequence-bearing workflow authority for the run."
        ),
        examples=["lotus-advise"],
    )
    current_summary_note: str = Field(
        description="Single lotus-ai supportability summary note for the workflow-pack run.",
        examples=["Run completed but still requires bounded human review before downstream use."],
    )
    replacement_run_id: str | None = Field(
        default=None,
        description="Replacement workflow-pack run identifier when the current run is historical.",
    )
    findings: list[WorkspaceAssistantWorkflowPackRunFinding] = Field(
        default_factory=list,
        description="Workflow-pack supportability findings preserved from lotus-ai.",
    )


class WorkspaceAssistantWorkflowPackRunReviewActionRequest(BaseModel):
    run_id: str = Field(
        description="Workflow-pack run identifier to update through the bounded review boundary.",
        examples=["packrun_workspace_rationale_req_001"],
        min_length=1,
        max_length=_WORKSPACE_ASSISTANT_RUN_ID_MAX_LENGTH,
    )
    action_type: WorkspaceAssistantWorkflowPackRunReviewActionType = Field(
        description="Bounded review action requested for the workspace rationale run.",
        examples=["SUPERSEDE"],
    )
    reviewed_by: str = Field(
        description="Actor identifier applying the bounded review action.",
        examples=["advisor_123"],
        max_length=_WORKSPACE_ASSISTANT_ACTOR_ID_MAX_LENGTH,
    )
    reason: str = Field(
        description="Short reviewer rationale captured alongside the workflow-pack review action.",
        examples=["A newer workspace rationale run supersedes this earlier draft."],
        min_length=1,
        max_length=_WORKSPACE_ASSISTANT_REVIEW_REASON_MAX_LENGTH,
    )
    replacement_run_id: str | None = Field(
        default=None,
        description=(
            "Replacement workflow-pack run identifier when the review action records "
            "replacement lineage."
        ),
        examples=["packrun_workspace_rationale_req_002"],
        min_length=1,
        max_length=_WORKSPACE_ASSISTANT_RUN_ID_MAX_LENGTH,
    )

    @field_validator("run_id")
    @classmethod
    def _normalize_run_id(cls, value: str) -> str:
        return _normalize_bounded_run_id(value, error_code="WORKSPACE_ASSISTANT_RUN_ID_REQUIRED")

    @field_validator("reviewed_by")
    @classmethod
    def _normalize_reviewed_by(cls, value: str) -> str:
        normalized = normalize_required_actor_id(
            value,
            error_code="WORKSPACE_ASSISTANT_REVIEW_ACTOR_REQUIRED",
        )
        if len(normalized) > _WORKSPACE_ASSISTANT_ACTOR_ID_MAX_LENGTH:
            raise ValueError("WORKSPACE_ASSISTANT_REVIEW_ACTOR_TOO_LONG")
        return cast(str, normalized)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = _normalize_workspace_assistant_text(
            value,
            error_code="WORKSPACE_ASSISTANT_REVIEW_REASON_REQUIRED",
        )
        if len(normalized) > _WORKSPACE_ASSISTANT_REVIEW_REASON_MAX_LENGTH:
            raise ValueError("WORKSPACE_ASSISTANT_REVIEW_REASON_TOO_LONG")
        return normalized

    @field_validator("replacement_run_id")
    @classmethod
    def _normalize_replacement_run_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_bounded_run_id(
            value,
            error_code="WORKSPACE_ASSISTANT_REPLACEMENT_RUN_ID_REQUIRED",
        )

    @model_validator(mode="after")
    def validate_replacement_lineage(
        self,
    ) -> "WorkspaceAssistantWorkflowPackRunReviewActionRequest":
        requires_replacement = self.action_type in {"REVISE", "SUPERSEDE"}
        has_replacement = isinstance(self.replacement_run_id, str) and bool(
            self.replacement_run_id.strip()
        )
        if requires_replacement and not has_replacement:
            raise ValueError("replacement_run_id is required for REVISE and SUPERSEDE actions")
        if not requires_replacement:
            self.replacement_run_id = None
        return self


class WorkspaceAssistantWorkflowPackRunReviewActionResponse(BaseModel):
    workflow_pack_run: WorkspaceAssistantWorkflowPackRun = Field(
        description="Workflow-pack run posture returned after the bounded review action completes.",
    )
    summary: list[str] = Field(
        default_factory=list,
        description="Bounded review summary notes preserved from lotus-ai.",
        examples=[["Run accepted and ready for bounded downstream use."]],
    )


class WorkspaceAssistantResponse(BaseModel):
    assistant_output: str = Field(
        description="Evidence-grounded advisory rationale produced through the Lotus AI boundary.",
        examples=["The draft remains READY and proposes a modest growth reallocation."],
    )
    generated_by: str = Field(
        description="Authority used to generate the advisory assistant output.",
        examples=["lotus-ai"],
    )
    evidence: WorkspaceAssistantEvidence = Field(
        description="Deterministic evidence bundle supplied to the AI assistance workflow.",
    )
    workflow_pack_run: WorkspaceAssistantWorkflowPackRun | None = Field(
        default=None,
        description=(
            "Bounded lotus-ai workflow-pack run posture preserved for this workspace rationale "
            "when the governed explicit execution boundary succeeds."
        ),
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


def _normalize_workspace_assistant_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def _normalize_bounded_run_id(value: str, *, error_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(error_code)
    if len(normalized) > _WORKSPACE_ASSISTANT_RUN_ID_MAX_LENGTH:
        raise ValueError("WORKSPACE_ASSISTANT_RUN_ID_TOO_LONG")
    return normalized
