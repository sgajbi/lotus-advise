from typing import Literal, Optional, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.common.actors import normalize_required_actor_id
from src.core.workspace.draft_models import WorkspaceEvaluationSummary
from src.core.workspace.input_models import WorkspaceInputMode, WorkspaceResolvedContext

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
