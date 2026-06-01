from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.business_text import normalize_required_copilot_business_text
from src.core.advisory_copilot.type_models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotClientReadyPosture,
    CopilotEvidenceAccessClass,
    CopilotReviewPosture,
    CopilotSourceDependency,
)

_COPILOT_AUDIENCE_LIMIT = 5


class CopilotActionDefinition(BaseModel):
    action_family: CopilotActionFamily = Field(
        description="Stable supported governed advisory copilot action family.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    display_name: str = Field(
        description="Business-facing action name for advisor and reviewer surfaces.",
        examples=["Proposal explanation"],
    )
    business_purpose: str = Field(
        description="Private-banking business purpose for the bounded copilot action.",
        examples=["Explain proposal evidence for advisor review."],
    )
    supported_audiences: tuple[CopilotAudience, ...] = Field(
        description="Audiences allowed to request or review the action.",
        examples=[["ADVISOR", "DESK_HEAD"]],
        min_length=1,
        max_length=_COPILOT_AUDIENCE_LIMIT,
    )
    required_source_dependencies: tuple[CopilotSourceDependency, ...] = Field(
        description="Implementation-backed sources required before the action can be supported.",
        examples=[["RFC0023_PROPOSAL_NARRATIVE", "RFC0024_PROPOSAL_MEMO"]],
    )
    output_evidence_classes: tuple[CopilotEvidenceAccessClass, ...] = Field(
        description="Evidence access classes produced or referenced by this action.",
        examples=[["ADVISOR_USE_SUMMARY"]],
    )
    workflow_pack_id: str = Field(
        description="Approved lotus-ai workflow-pack identifier reserved for this action family.",
        examples=["advisory_copilot_proposal_explanation.pack"],
    )
    workflow_pack_version: str = Field(
        default="v1",
        description="Workflow-pack version expected by supported copilot integration.",
        examples=["v1"],
    )
    workbench_surface_key: str = Field(
        description=(
            "Workbench surface key that may render this action after Gateway support exists."
        ),
        examples=["advisory_copilot.proposal_explanation"],
    )
    default_review_posture: CopilotReviewPosture = Field(
        default="REVIEW_REQUIRED",
        description="Default review posture for generated copilot output.",
        examples=["REVIEW_REQUIRED"],
    )
    client_ready_publication: CopilotClientReadyPosture = Field(
        default="BLOCKED",
        description="Client-ready publication posture for all supported copilot output.",
        examples=["BLOCKED"],
    )


class CopilotBusinessProjection(BaseModel):
    action_family: CopilotActionFamily = Field(
        description="Action family represented by the business-facing projection.",
        examples=["MEETING_PREPARATION"],
    )
    label: str = Field(
        description="Business-facing label safe for advisor and reviewer surfaces.",
        examples=["Meeting preparation"],
    )
    summary: str = Field(
        description="Business-facing summary safe for UI, report, wiki, and commercial copy.",
        examples=["Prepare an advisor-reviewed meeting note from source-backed evidence."],
    )
    next_action_label: str = Field(
        description="Business-facing next action label that does not expose technical internals.",
        examples=["Review draft"],
    )

    @field_validator("label", "summary", "next_action_label")
    @classmethod
    def _business_copy_must_be_safe(cls, value: str) -> str:
        return normalize_required_copilot_business_text(
            value,
            error_code="COPILOT_BUSINESS_PROJECTION_REQUIRED",
        )
