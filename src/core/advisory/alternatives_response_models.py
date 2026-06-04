from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_types import (
    AlternativeCandidateStatus,
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
    AlternativeStatus,
)


class AlternativeConstraintResult(BaseModel):
    constraint_name: str = Field(description="Constraint identifier applied to the alternative.")
    status: Literal["PASSED", "FAILED", "NOT_EVALUATED"] = Field(
        description="Outcome of the constraint evaluation.",
    )
    summary: str = Field(description="Advisor-facing constraint evaluation summary.")
    reason_code: str | None = Field(
        default=None,
        description="Stable reason code when the constraint fails or cannot be evaluated.",
    )


class AlternativeTradeoff(BaseModel):
    tradeoff_code: str = Field(description="Stable tradeoff code.")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Tradeoff severity.")
    summary: str = Field(description="Advisor-facing tradeoff summary.")


class AlternativeComparisonSummary(BaseModel):
    headline: str = Field(description="Short summary headline for the alternative.")
    primary_tradeoff: str = Field(description="Primary tradeoff summary.")
    improvements: list[str] = Field(default_factory=list, description="Improvement highlights.")
    deteriorations: list[str] = Field(default_factory=list, description="Deterioration highlights.")
    unchanged_material_factors: list[str] = Field(
        default_factory=list,
        description="Material factors that remain unchanged.",
    )
    approval_delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Approval posture delta relative to the baseline proposal.",
    )
    risk_delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Risk lens delta relative to the baseline proposal.",
    )
    allocation_delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Allocation-lens delta relative to the baseline proposal.",
    )
    cash_delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Cash delta relative to the baseline proposal.",
    )
    currency_delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Currency exposure delta relative to the baseline proposal.",
    )
    cost_delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Cost and friction delta relative to the baseline proposal.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting this comparison summary.",
    )


class AlternativeCandidateSeed(BaseModel):
    candidate_id: str = Field(description="Deterministic candidate identifier.")
    objective: AlternativeConstructionObjective = Field(
        description="Construction objective that produced this seed."
    )
    strategy_id: str = Field(description="Deterministic strategy identifier.")
    status: AlternativeCandidateStatus = Field(
        default="PROVISIONAL",
        description="Current candidate seed posture before canonical simulation.",
    )
    label: str = Field(description="Short advisor-facing label for the candidate seed.")
    summary: str = Field(description="Strategy summary for the candidate seed.")
    required_evidence: list[AlternativeEvidenceRequirement] = Field(
        default_factory=list,
        description="Upstream evidence requirements declared by the strategy.",
    )
    generated_intents: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministic generated proposal intents prepared for downstream simulation.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy metadata required for downstream simulation and ranking.",
    )


class RejectedAlternativeCandidate(BaseModel):
    candidate_id: str = Field(description="Deterministic rejected candidate identifier.")
    objective: AlternativeConstructionObjective = Field(
        description="Construction objective associated with the rejected candidate."
    )
    status: AlternativeStatus = Field(
        description="Rejected status explaining why the candidate cannot proceed."
    )
    reason_code: str = Field(description="Stable rejected-candidate reason code.")
    summary: str = Field(description="Advisor-facing rejected-candidate summary.")
    failed_constraints: list[str] = Field(
        default_factory=list,
        description="Constraint names that blocked the candidate.",
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Missing evidence identifiers associated with the rejection.",
    )
    remediation: str | None = Field(
        default=None,
        description="Advisor-facing remediation guidance for the rejection.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the rejection.",
    )


class AlternativeRankingProjection(BaseModel):
    ranking_reason_codes: list[str] = Field(
        default_factory=list,
        description="Stable reason codes explaining the final ranking position.",
    )
    ranked_against_alternative_ids: list[str] = Field(
        default_factory=list,
        description="Alternative ids directly compared during final ranking.",
    )
    comparator_inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Stable comparator inputs used for deterministic ordering.",
    )


class ProposalAlternative(BaseModel):
    alternative_id: str = Field(description="Deterministic alternative identifier.")
    label: str = Field(description="Advisor-facing alternative label.")
    objective: AlternativeConstructionObjective = Field(
        description="Construction objective represented by the alternative."
    )
    rank: int | None = Field(
        default=None,
        description="Deterministic rank assigned after alternatives ranking.",
    )
    selected: bool = Field(
        default=False,
        description="Whether this alternative is selected for persisted proposal state.",
    )
    status: AlternativeStatus = Field(description="Current alternative posture.")
    construction_policy_version: str = Field(
        description="Construction policy version used to generate the alternative."
    )
    ranking_policy_version: str = Field(
        description="Ranking policy version used to rank the alternative."
    )
    intents: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Generated intents associated with the alternative.",
    )
    simulation_result_ref: str | None = Field(
        default=None,
        description="Reference to canonical simulation evidence for this alternative.",
    )
    risk_lens_ref: str | None = Field(
        default=None,
        description="Reference to canonical risk evidence for this alternative.",
    )
    proposal_decision_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Canonical proposal decision summary projected for this alternative.",
    )
    comparison_summary: AlternativeComparisonSummary | None = Field(
        default=None,
        description="Deterministic comparison summary for the alternative.",
    )
    constraint_results: list[AlternativeConstraintResult] = Field(
        default_factory=list,
        description="Constraint evaluation results for the alternative.",
    )
    advisor_tradeoffs: list[AlternativeTradeoff] = Field(
        default_factory=list,
        description="Advisor-facing tradeoffs for the alternative.",
    )
    ranking_projection: AlternativeRankingProjection | None = Field(
        default=None,
        description="Deterministic ranking explanation for the alternative.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the alternative.",
    )


class ProposalAlternatives(BaseModel):
    requested_objectives: list[AlternativeConstructionObjective] = Field(
        default_factory=list,
        description="Normalized requested objective order used for alternatives generation.",
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected alternative id when persisted selection exists.",
    )
    candidate_generation_policy_id: str | None = Field(
        default=None,
        description="Candidate-generation policy identifier used for this alternatives run.",
    )
    ranking_policy_id: str | None = Field(
        default=None,
        description="Ranking policy identifier used for this alternatives run.",
    )
    alternatives: list[ProposalAlternative] = Field(
        default_factory=list,
        description="Deterministically ranked alternatives returned for the proposal.",
    )
    rejected_candidates: list[RejectedAlternativeCandidate] = Field(
        default_factory=list,
        description="Rejected candidates retained for advisor and operator visibility.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the alternatives envelope.",
    )


__all__ = [
    "AlternativeCandidateSeed",
    "AlternativeComparisonSummary",
    "AlternativeConstraintResult",
    "AlternativeRankingProjection",
    "AlternativeTradeoff",
    "ProposalAlternative",
    "ProposalAlternatives",
    "RejectedAlternativeCandidate",
]
