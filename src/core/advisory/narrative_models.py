from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ProposalNarrativeAudience = Literal["ADVISOR_REVIEW"]
ProposalNarrativeClientAudience = Literal["ADVISOR_REVIEW", "CLIENT_READY"]
ProposalNarrativeRequestedGenerationMode = Literal["DETERMINISTIC_TEMPLATE", "AI_ASSISTED_DRAFT"]
ProposalNarrativeGenerationMode = Literal["DETERMINISTIC_TEMPLATE", "AI_ASSISTED_DRAFT"]
ProposalNarrativeStatus = Literal[
    "READY_FOR_ADVISOR_REVIEW",
    "BLOCKED_INSUFFICIENT_EVIDENCE",
    "BLOCKED_POLICY_INCOMPLETE",
    "BLOCKED_GUARDRAIL_FAILURE",
]
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
ProposalNarrativeRiskPosture = Literal["STANDARD", "CONCENTRATION_REVIEW", "UNAVAILABLE"]
ProposalNarrativePolicyStatus = Literal["READY_FOR_ADVISOR_REVIEW", "BLOCKED_CLIENT_READY"]
ProposalNarrativeGuardrailStatus = Literal["PASS", "FAIL"]
ProposalNarrativeReviewAction = Literal["APPROVE", "REJECT", "REQUEST_REGENERATION"]
ProposalNarrativeReviewedState = Literal[
    "APPROVED_FOR_ADVISOR_USE",
    "REJECTED",
    "REGENERATION_REQUESTED",
]
ProposalNarrativeClientReadyStatus = Literal[
    "NOT_REQUESTED",
    "BLOCKED_REVIEW_REQUIRED",
    "BLOCKED_POLICY_OR_GUARDRAIL",
    "APPROVED_FOR_CLIENT_READY",
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
    jurisdiction: Optional[str] = Field(
        default=None,
        description=(
            "Optional booking or client jurisdiction used for deterministic disclosure policy "
            "selection. Unsupported or missing jurisdictions block client-ready posture."
        ),
        examples=["SG"],
    )
    product_types: List[str] = Field(
        default_factory=list,
        description=(
            "Optional product-type hints used for disclosure policy selection. When omitted, "
            "Slice 6 derives product types from proposal evidence where possible."
        ),
        examples=[["EQUITY", "FX"]],
    )
    client_audience: ProposalNarrativeClientAudience = Field(
        default="ADVISOR_REVIEW",
        description=(
            "Policy audience used for disclosure and promotion gating. Slice 6 may return a "
            "blocked policy result for `CLIENT_READY`, but does not promote client-ready output."
        ),
        examples=["ADVISOR_REVIEW"],
    )
    generation_mode: ProposalNarrativeRequestedGenerationMode = Field(
        default="DETERMINISTIC_TEMPLATE",
        description=(
            "Requested narrative generation mode. `AI_ASSISTED_DRAFT` is Slice 7 opt-in only, "
            "uses the governed lotus-ai workflow-pack adapter, and remains draft until later "
            "review slices."
        ),
        examples=["DETERMINISTIC_TEMPLATE"],
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


class ProposalNarrativePolicyContext(BaseModel):
    jurisdiction: str = Field(
        description="Resolved jurisdiction used by narrative policy.",
        examples=["SG"],
    )
    product_types: List[str] = Field(
        default_factory=list,
        description="Resolved product types used by disclosure policy.",
        examples=[["EQUITY", "FX"]],
    )
    risk_posture: ProposalNarrativeRiskPosture = Field(
        description="Resolved risk posture used by disclosure policy.",
        examples=["CONCENTRATION_REVIEW"],
    )
    client_audience: ProposalNarrativeClientAudience = Field(
        description="Policy audience used for promotion and disclosure gating.",
        examples=["ADVISOR_REVIEW"],
    )


class ProposalNarrativeDisclosure(BaseModel):
    disclosure_id: str = Field(
        description="Stable approved disclosure identifier.",
        examples=["DISC_SG_GENERAL_MARKET_RISK"],
    )
    jurisdiction: str = Field(description="Disclosure jurisdiction.", examples=["SG"])
    product_type: str = Field(description="Product type or posture the disclosure covers.")
    required_for: ProposalNarrativeClientAudience = Field(
        description="Audience for which this disclosure is required."
    )
    text: str = Field(description="Approved disclosure text selected by policy.")
    source_authority: str = Field(
        description="Policy authority that owns the disclosure text.",
        examples=["lotus-advise.rfc0023.slice6"],
    )
    policy_version: str = Field(
        description="Disclosure policy version that selected the disclosure.",
        examples=["advisory-narrative-policy.2026-05"],
    )


class ProposalNarrativeGuardrailResult(BaseModel):
    guardrail_id: str = Field(
        description="Stable guardrail identifier.",
        examples=["GR_UNSUPPORTED_GUARANTEE_CLAIM"],
    )
    status: ProposalNarrativeGuardrailStatus = Field(description="Guardrail evaluation status.")
    message: str = Field(description="Human-readable guardrail result.")
    section_key: Optional[ProposalNarrativeSectionKey] = Field(
        default=None,
        description="Section key that triggered the guardrail result, when applicable.",
    )


class ProposalNarrativePolicy(BaseModel):
    policy_version: str = Field(
        description="Narrative policy version used for disclosure and guardrail decisions.",
        examples=["advisory-narrative-policy.2026-05"],
    )
    status: ProposalNarrativePolicyStatus = Field(description="Policy readiness status.")
    context: ProposalNarrativePolicyContext = Field(
        description="Resolved policy context for the narrative."
    )
    required_disclosures: List[ProposalNarrativeDisclosure] = Field(
        default_factory=list,
        description="Approved disclosures selected by deterministic policy.",
    )
    client_ready_blockers: List[str] = Field(
        default_factory=list,
        description="Policy blockers preventing client-ready posture.",
    )
    prohibited_claims: List[str] = Field(
        default_factory=list,
        description="Unsupported claim patterns rejected by narrative guardrails.",
    )


class ProposalNarrativeAiLineage(BaseModel):
    requested_generation_mode: ProposalNarrativeRequestedGenerationMode = Field(
        description="Generation mode requested by the caller.",
        examples=["AI_ASSISTED_DRAFT"],
    )
    adapter_version: str = Field(
        description="lotus-advise adapter version used for proposal narrative AI handoff.",
        examples=["proposal-narrative-lotus-ai-adapter.v1"],
    )
    workflow_pack_id: str = Field(
        description="lotus-ai workflow-pack identifier used for AI-assisted narrative generation.",
        examples=["proposal_narrative_draft.pack"],
    )
    workflow_pack_version: str = Field(
        description="lotus-ai workflow-pack version requested by the adapter.",
        examples=["v1"],
    )
    prompt_template_version: str = Field(
        description="Approved prompt/instruction template version used by the adapter.",
        examples=["proposal-narrative-instructions.v1"],
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Model version reported by lotus-ai, when available.",
        examples=["lotus-ai-governed-model.v1"],
    )
    workflow_run_id: Optional[str] = Field(
        default=None,
        description="lotus-ai workflow run identifier, when AI generation completed.",
        examples=["packrun_proposal_narrative_001"],
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Fallback reason when deterministic template output is returned instead.",
        examples=["LOTUS_AI_NARRATIVE_UNAVAILABLE"],
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
        description=(
            "Actual generation mode used for this narrative. AI-assisted output remains draft "
            "and is never client-ready in RFC-0023 Slice 7."
        ),
    )
    review_state: ProposalNarrativeReviewState = Field(
        default="DRAFT",
        description="Review state. Slice 5 creates advisor-review draft only.",
    )
    policy_version: str = Field(
        description="Narrative policy or template version used for deterministic rendering.",
        examples=["proposal-narrative-deterministic.v1"],
    )
    narrative_policy: ProposalNarrativePolicy = Field(
        description="Resolved narrative policy, disclosure selection, and promotion blockers."
    )
    ai_lineage: Optional[ProposalNarrativeAiLineage] = Field(
        default=None,
        description=(
            "AI adapter lineage or deterministic fallback evidence for AI-assisted requests."
        ),
    )
    grounding_packet: ProposalNarrativeGroundingPacket = Field(
        description="Grounding packet used by deterministic narrative rendering."
    )
    sections: List[ProposalNarrativeSection] = Field(
        default_factory=list,
        description="Ordered deterministic narrative sections.",
    )
    disclosures: List[ProposalNarrativeDisclosure] = Field(
        default_factory=list,
        description="Approved disclosures selected by deterministic narrative policy.",
    )
    guardrail_results: List[ProposalNarrativeGuardrailResult] = Field(
        default_factory=list,
        description="Deterministic unsupported-claim and source-reference guardrail results.",
    )
    limitations: List[ProposalNarrativeMissingEvidence] = Field(
        default_factory=list,
        description="Explicit limitations and missing evidence for this narrative.",
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
            "Whether the reviewer is requesting client-ready release posture. Slice 8 only "
            "permits this when policy and guardrails are already clear."
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
