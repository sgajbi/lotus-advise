from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.core.proposal_result_models import ProposalResult
from src.core.workspace.draft_models import (
    WorkspaceDraftState,
    WorkspaceEvaluationSummary,
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

_INPUT_MODE_PAYLOAD_FIELDS = {
    "stateless": ("stateless_input", "stateful_input"),
    "stateful": ("stateful_input", "stateless_input"),
}


def _validate_workspace_input_mode_payloads(
    *,
    input_mode: WorkspaceInputMode,
    stateless_input: WorkspaceStatelessInput | None,
    stateful_input: WorkspaceStatefulInput | None,
    subject: str,
) -> None:
    payloads = {
        "stateless_input": stateless_input,
        "stateful_input": stateful_input,
    }
    required_field, excluded_field = _INPUT_MODE_PAYLOAD_FIELDS[input_mode]
    if payloads[required_field] is None or payloads[excluded_field] is not None:
        raise ValueError(
            f"{input_mode} {subject} require {required_field} and must not include {excluded_field}"
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
        _validate_workspace_input_mode_payloads(
            input_mode=self.input_mode,
            stateless_input=self.stateless_input,
            stateful_input=self.stateful_input,
            subject="workspaces",
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
        _validate_workspace_input_mode_payloads(
            input_mode=self.input_mode,
            stateless_input=self.stateless_input,
            stateful_input=self.stateful_input,
            subject="workspace sessions",
        )
        return self


class WorkspaceSessionCreateResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Created advisory workspace session.",
    )
