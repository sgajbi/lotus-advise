from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ProposalNarrativeAudience = Literal["ADVISOR_REVIEW"]
ProposalNarrativeGenerationMode = Literal["DETERMINISTIC_TEMPLATE"]
ProposalNarrativeStatus = Literal["READY_FOR_ADVISOR_REVIEW", "BLOCKED_INSUFFICIENT_EVIDENCE"]
ProposalNarrativeReviewState = Literal["DRAFT"]
ProposalNarrativeSectionKey = Literal[
    "EXECUTIVE_SUMMARY",
    "RECOMMENDATION_RATIONALE",
    "RISK_AND_CONCENTRATION",
    "SUITABILITY_AND_MANDATE",
    "MATERIAL_CHANGES",
    "ALTERNATIVES_CONSIDERED",
    "APPROVALS_AND_NEXT_STEPS",
    "LIMITATIONS_AND_DISCLOSURES",
]


class ProposalNarrativeRequest(BaseModel):
    audience: ProposalNarrativeAudience = Field(
        default="ADVISOR_REVIEW",
        description=(
            "Narrative audience requested by the caller. Slice 5 supports advisor-review "
            "narrative only; client-draft and client-ready commentary remain gated."
        ),
        examples=["ADVISOR_REVIEW"],
    )
    sections: List[ProposalNarrativeSectionKey] = Field(
        default_factory=list,
        description=(
            "Optional ordered section allowlist. Empty means all deterministic advisor-review "
            "sections are returned in canonical order."
        ),
        examples=[["EXECUTIVE_SUMMARY", "RISK_AND_CONCENTRATION"]],
    )
    requested_by: Optional[str] = Field(
        default=None,
        description="Optional actor identifier requesting deterministic advisor-review narrative.",
        examples=["advisor_123"],
    )


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


class ProposalNarrativeSection(BaseModel):
    section_key: ProposalNarrativeSectionKey = Field(
        description="Canonical narrative section key.", examples=["EXECUTIVE_SUMMARY"]
    )
    title: str = Field(description="Advisor-facing section title.", examples=["Executive Summary"])
    text: str = Field(
        description="Deterministic narrative text derived only from grounding packet facts.",
        examples=["Proposal status is READY and requires client consent."],
    )
    source_refs: List[ProposalNarrativeSourceRef] = Field(
        default_factory=list,
        description="Source references used for this section.",
    )
    limitation_refs: List[str] = Field(
        default_factory=list,
        description="Missing evidence keys or limitations relevant to this section.",
    )


class ProposalNarrative(BaseModel):
    narrative_id: str = Field(
        description="Deterministic narrative identifier for this transient artifact narrative.",
        examples=["pn_abc12345"],
    )
    status: ProposalNarrativeStatus = Field(description="Narrative generation status.")
    audience: ProposalNarrativeAudience = Field(description="Narrative audience.")
    generation_mode: ProposalNarrativeGenerationMode = Field(
        default="DETERMINISTIC_TEMPLATE",
        description="Generation mode. Slice 5 uses no model or AI workflow call.",
    )
    review_state: ProposalNarrativeReviewState = Field(
        default="DRAFT",
        description="Review state. Slice 5 creates advisor-review draft only.",
    )
    policy_version: str = Field(
        description="Narrative policy or template version used for deterministic rendering.",
        examples=["proposal-narrative-deterministic.v1"],
    )
    grounding_packet: ProposalNarrativeGroundingPacket = Field(
        description="Grounding packet used by deterministic narrative rendering."
    )
    sections: List[ProposalNarrativeSection] = Field(
        default_factory=list,
        description="Ordered deterministic narrative sections.",
    )
    limitations: List[ProposalNarrativeMissingEvidence] = Field(
        default_factory=list,
        description="Explicit limitations and missing evidence for this narrative.",
    )
