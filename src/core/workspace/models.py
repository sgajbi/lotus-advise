from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.core.proposals.models import ProposalCreateResponse
from src.core.workspace import assistant_models as _assistant_models
from src.core.workspace.action_models import (
    WorkspaceDraftActionRequest as WorkspaceDraftActionRequest,
)
from src.core.workspace.action_models import (
    WorkspaceDraftActionResponse as WorkspaceDraftActionResponse,
)
from src.core.workspace.action_models import (
    WorkspaceDraftActionType as WorkspaceDraftActionType,
)
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
    WorkspaceDraftState as WorkspaceDraftState,
)
from src.core.workspace.draft_models import (
    WorkspaceEvaluationImpactSummary as WorkspaceEvaluationImpactSummary,
)
from src.core.workspace.draft_models import (
    WorkspaceEvaluationSummary as WorkspaceEvaluationSummary,
)
from src.core.workspace.draft_models import (
    WorkspaceTradeDraft as WorkspaceTradeDraft,
)
from src.core.workspace.input_models import (
    WorkspaceInputMode as WorkspaceInputMode,
)
from src.core.workspace.input_models import (
    WorkspaceResolvedContext as WorkspaceResolvedContext,
)
from src.core.workspace.input_models import (
    WorkspaceStatefulInput as WorkspaceStatefulInput,
)
from src.core.workspace.input_models import (
    WorkspaceStatelessInput as WorkspaceStatelessInput,
)
from src.core.workspace.save_models import (
    WorkspaceResumeRequest as WorkspaceResumeRequest,
)
from src.core.workspace.save_models import (
    WorkspaceSavedVersionListResponse as WorkspaceSavedVersionListResponse,
)
from src.core.workspace.save_models import (
    WorkspaceSaveRequest as WorkspaceSaveRequest,
)
from src.core.workspace.save_models import (
    WorkspaceSaveResponse as WorkspaceSaveResponse,
)
from src.core.workspace.session_models import (
    WorkspaceLifecycleState as WorkspaceLifecycleState,
)
from src.core.workspace.session_models import (
    WorkspaceSession as WorkspaceSession,
)
from src.core.workspace.session_models import (
    WorkspaceSessionCreateRequest as WorkspaceSessionCreateRequest,
)
from src.core.workspace.session_models import (
    WorkspaceSessionCreateResponse as WorkspaceSessionCreateResponse,
)
from src.core.workspace.version_models import (
    WorkspaceLifecycleLink as WorkspaceLifecycleLink,
)
from src.core.workspace.version_models import (
    WorkspaceReplayEvidence as WorkspaceReplayEvidence,
)
from src.core.workspace.version_models import (
    WorkspaceSavedVersion as WorkspaceSavedVersion,
)
from src.core.workspace.version_models import (
    WorkspaceSavedVersionSummary as WorkspaceSavedVersionSummary,
)

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
