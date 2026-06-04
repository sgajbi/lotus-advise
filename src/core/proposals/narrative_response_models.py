from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_envelope_models import ProposalNarrative
from src.core.advisory.narrative_review_models import ProposalNarrativeReviewRecord
from src.core.advisory.narrative_types import (
    ProposalNarrativeClientAudience,
    ProposalNarrativeGenerationMode,
    ProposalNarrativeSectionKey,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalSummary,
    ProposalWorkflowEvent,
)


class ProposalNarrativeReadResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary for the immutable version that owns the narrative."
    )
    proposal_version_no: int = Field(
        description="Immutable proposal version number containing the persisted narrative.",
        examples=[1],
    )
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.", examples=["ppv_001"]
    )
    proposal_narrative: ProposalNarrative = Field(
        description="Exact persisted proposal narrative from the immutable proposal artifact."
    )
    narrative_review: Optional[ProposalNarrativeReviewRecord] = Field(
        default=None,
        description="Latest review event for this narrative, when one has been recorded.",
    )
    source_narrative_hash: str = Field(
        description="Canonical hash of the persisted narrative payload.",
        examples=["sha256:abc123"],
    )
    replay_evidence_path: str = Field(
        description="Canonical replay-evidence route for the owning proposal version.",
        examples=["/advisory/proposals/pp_001/versions/1/replay-evidence"],
    )
    read_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Read-only posture proving the route does not mutate the proposal version or "
            "promote client-ready publication."
        ),
        examples=[
            {
                "source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
                "mutation_performed": False,
                "client_ready_publication": "GATED",
            }
        ],
    )


class ProposalNarrativeRegenerationRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting the regenerated advisor-review narrative candidate.",
        examples=["advisor_123"],
    )
    reason: str = Field(
        description="Human-readable reason for regeneration, captured for caller audit context.",
        examples=["Refresh advisor wording after review feedback."],
    )
    sections: Optional[List[ProposalNarrativeSectionKey]] = Field(
        default=None,
        description=(
            "Optional ordered section allowlist. When omitted, the current persisted narrative "
            "section set is regenerated."
        ),
        examples=[["EXECUTIVE_SUMMARY", "RISK_AND_CONCENTRATION"]],
    )
    generation_mode: ProposalNarrativeGenerationMode = Field(
        default="DETERMINISTIC_TEMPLATE",
        description=(
            "Regeneration mode. Deterministic template mode is the default; AI-assisted draft "
            "mode remains advisor-review only and still requires later review."
        ),
        examples=["DETERMINISTIC_TEMPLATE"],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional jurisdiction override for policy/disclosure selection.",
        examples=["SG"],
    )
    product_types: Optional[List[str]] = Field(
        default=None,
        description="Optional product-type override for disclosure policy selection.",
        examples=[["EQUITY", "FX"]],
    )
    client_audience: ProposalNarrativeClientAudience = Field(
        default="ADVISOR_REVIEW",
        description=(
            "Policy audience for the regenerated candidate. Client-ready publication remains "
            "gated even when this asks policy to evaluate client-ready blockers."
        ),
        examples=["ADVISOR_REVIEW"],
    )


class ProposalNarrativeRegenerationResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary for the immutable version used as regeneration source."
    )
    proposal_version_no: int = Field(
        description="Immutable proposal version number used as regeneration source.",
        examples=[1],
    )
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.", examples=["ppv_001"]
    )
    current_narrative_id: str = Field(
        description="Narrative id currently persisted on the immutable proposal version.",
        examples=["pn_current_001"],
    )
    regenerated_narrative: ProposalNarrative = Field(
        description=(
            "Non-persisted regenerated advisor-review narrative candidate built from the "
            "immutable proposal artifact."
        )
    )
    current_source_narrative_hash: str = Field(
        description="Canonical hash of the current persisted narrative payload.",
        examples=["sha256:abc123"],
    )
    regenerated_source_narrative_hash: str = Field(
        description="Canonical hash of the regenerated narrative candidate payload.",
        examples=["sha256:def456"],
    )
    source_artifact_hash: str = Field(
        description="Artifact hash of the immutable proposal version used for regeneration.",
        examples=["sha256:artifact"],
    )
    source_request_hash: str = Field(
        description="Request hash of the immutable proposal version used for regeneration.",
        examples=["sha256:request"],
    )
    latest_narrative_review: Optional[ProposalNarrativeReviewRecord] = Field(
        default=None,
        description="Latest review event for the current persisted narrative, when present.",
    )
    materially_changed: bool = Field(
        description="Whether the regenerated candidate hash differs from the persisted narrative.",
        examples=[False],
    )
    regeneration_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Governed posture proving regeneration is non-persistent and still review-gated."
        ),
        examples=[
            {
                "source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
                "persistence_status": "NOT_PERSISTED_REVIEW_REQUIRED",
                "mutation_performed": False,
                "client_ready_publication": "GATED",
                "review_required_before_report_package": True,
            }
        ],
    )


class ProposalNarrativeReviewResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured after narrative review recording.",
        examples=[{"proposal_id": "pp_001", "current_version_no": 1}],
    )
    narrative_review: ProposalNarrativeReviewRecord = Field(
        description="Persisted narrative review event projection.",
        examples=[
            {
                "review_id": "pwe_narrative_review_001",
                "proposal_id": "pp_001",
                "proposal_version_no": 1,
                "narrative_id": "pn_001",
                "action": "APPROVE",
                "review_state": "APPROVED_FOR_ADVISOR_USE",
                "client_ready_status": "NOT_REQUESTED",
                "reviewed_by": "compliance_reviewer_001",
                "reviewed_at": "2026-05-22T08:30:00+00:00",
                "reason": "Narrative is evidence-grounded and suitable for advisor use.",
                "source_narrative_hash": "sha256:9c8a2f1d",
                "replacement_narrative_id": None,
                "replayed": False,
            }
        ],
    )
    latest_workflow_event: ProposalWorkflowEvent = Field(
        description="Append-only workflow event created or replayed for this narrative review.",
        examples=[{"event_type": "NARRATIVE_REVIEWED", "to_state": "DRAFT"}],
    )
