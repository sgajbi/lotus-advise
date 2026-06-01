from typing import Any, Optional

from pydantic import BaseModel, Field

from src.core.proposal_result_models import ProposalResult
from src.core.workspace.draft_models import WorkspaceDraftState, WorkspaceEvaluationSummary
from src.core.workspace.input_models import WorkspaceInputMode, WorkspaceResolvedContext


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
        description=(
            "Canonical hash of the simulation request used for the latest deterministic evaluation."
        ),
        examples=["2fd1f3c2ecde4e86fbeb5dff19df8fd5b4b9e24473e7a17f80f4d3d57f644ca8"],
    )
    captured_at: str = Field(
        description="UTC ISO8601 timestamp when replay evidence was captured.",
        examples=["2026-03-25T09:45:00+00:00"],
    )
    continuity: dict[str, str | int | None] = Field(
        default_factory=dict,
        description=(
            "Normalized continuity metadata linking the workspace replay evidence into lifecycle "
            "and async replay surfaces when applicable."
        ),
        examples=[
            {
                "workspace_version_id": "awv_001",
                "proposal_id": "pp_001",
                "proposal_version_no": 1,
                "handoff_action": "CREATED_PROPOSAL",
            }
        ],
    )
    risk_lens: Optional[dict[str, Any]] = Field(
        default=None,
        description="Normalized proposal risk-lens evidence captured for the latest evaluation.",
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
