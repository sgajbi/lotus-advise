from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from src.core.advisory.narrative_types import ProposalNarrativeAudience


class ProposalNarrativeSourceRef(BaseModel):
    ref_type: Literal[
        "proposal_artifact",
        "proposal_result",
        "decision_summary",
        "risk_lens",
        "suitability",
        "alternatives",
        "limitations",
    ] = Field(description="Grounding source reference type.", examples=["decision_summary"])
    ref_id: str = Field(description="Stable source reference identifier.", examples=["pa_001"])
    field_path: str = Field(
        description="Field path inside the source evidence used by the section.",
        examples=["proposal_decision_summary.decision_status"],
    )


class ProposalNarrativeMissingEvidence(BaseModel):
    evidence_key: Literal[
        "risk_lens",
        "suitability",
        "alternatives",
        "mandate_policy",
        "disclosure_policy",
        "review_workflow",
        "report_archive_lineage",
    ] = Field(description="Missing or unavailable evidence key.", examples=["risk_lens"])
    required_for: str = Field(
        description="Narrative use or promotion gate that requires this evidence.",
        examples=["client-ready narrative"],
    )
    message: str = Field(
        description="Advisor-readable blocked or degraded evidence explanation.",
        examples=["Risk lens is unavailable for this proposal run."],
    )


class ProposalNarrativeGroundingPacket(BaseModel):
    packet_id: str = Field(
        description="Deterministic grounding packet identifier.", examples=["pgp_abc12345"]
    )
    policy_version: str = Field(
        description="Deterministic narrative policy version.",
        examples=["proposal-narrative-deterministic.v1"],
    )
    audience: ProposalNarrativeAudience = Field(description="Narrative audience.")
    source_refs: List[ProposalNarrativeSourceRef] = Field(
        default_factory=list,
        description="Allowed source references supplied to deterministic narrative rendering.",
    )
    input_hashes: Dict[str, str] = Field(
        default_factory=dict,
        description="Available source-input hashes used to bind narrative to proposal evidence.",
        examples=[{"request_hash": "sha256:abc", "artifact_hash": "sha256:def"}],
    )
    facts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Small deterministic fact set extracted from allowed proposal evidence.",
    )
    missing_evidence: List[ProposalNarrativeMissingEvidence] = Field(
        default_factory=list,
        description="Explicit missing evidence that limits narrative readiness or audience scope.",
    )
