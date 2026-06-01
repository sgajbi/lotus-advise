from typing import Optional

from pydantic import BaseModel, Field

from src.core.workspace.draft_models import WorkspaceEvaluationSummary
from src.core.workspace.version_models import WorkspaceReplayEvidence, WorkspaceSavedVersion


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
