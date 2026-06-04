from typing import Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_types import (
    ProposalNarrativeClientReadyStatus,
    ProposalNarrativeReviewAction,
    ProposalNarrativeReviewedState,
)


class ProposalNarrativeReviewRequest(BaseModel):
    action: ProposalNarrativeReviewAction = Field(
        description="Bounded review action for the persisted proposal narrative version.",
        examples=["APPROVE"],
    )
    reviewed_by: str = Field(
        description="Actor id recording the narrative review decision.",
        examples=["compliance_reviewer_001"],
    )
    reason: str = Field(
        description="Human-readable review rationale captured for audit.",
        examples=["Narrative is evidence-grounded and suitable for advisor use."],
    )
    client_ready_release_requested: bool = Field(
        default=False,
        description=(
            "Whether the reviewer requested client-ready release posture. Current RFC-0023 "
            "support records the request for audit but keeps client-ready release blocked until "
            "separately approved client-ready policy, disclosure, report/render/archive, and "
            "publication controls are implemented."
        ),
        examples=[False],
    )
    replacement_narrative_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional replacement narrative identifier when this review supersedes a prior draft."
        ),
        examples=["pn_replacement_001"],
    )


class ProposalNarrativeReviewRecord(BaseModel):
    review_id: str = Field(
        description="Review event identifier for this persisted narrative review.",
        examples=["pwe_narrative_review_001"],
    )
    proposal_id: str = Field(description="Proposal aggregate identifier.", examples=["pp_001"])
    proposal_version_no: int = Field(description="Reviewed immutable proposal version number.")
    narrative_id: str = Field(description="Reviewed narrative identifier.", examples=["pn_001"])
    action: ProposalNarrativeReviewAction = Field(
        description="Review action recorded.",
        examples=["APPROVE"],
    )
    review_state: ProposalNarrativeReviewedState = Field(
        description="Resulting narrative review state.",
        examples=["APPROVED_FOR_ADVISOR_USE"],
    )
    client_ready_status: ProposalNarrativeClientReadyStatus = Field(
        description="Client-ready release posture after this review action.",
        examples=["NOT_REQUESTED"],
    )
    reviewed_by: str = Field(
        description="Actor id that recorded the review.",
        examples=["compliance_reviewer_001"],
    )
    reviewed_at: str = Field(
        description="UTC ISO8601 review timestamp.",
        examples=["2026-05-22T08:30:00+00:00"],
    )
    reason: str = Field(
        description="Review rationale captured for audit.",
        examples=["Narrative is evidence-grounded and suitable for advisor use."],
    )
    source_narrative_hash: str = Field(
        description="Canonical hash of the reviewed narrative payload.",
        examples=["sha256:9c8a2f1d"],
    )
    replacement_narrative_id: Optional[str] = Field(
        default=None,
        description="Replacement narrative identifier requested by regeneration review, if any.",
        examples=["pn_replacement_001"],
    )
    replayed: bool = Field(
        default=False,
        description="Whether this response is an idempotent replay of an existing review event.",
        examples=[False],
    )
