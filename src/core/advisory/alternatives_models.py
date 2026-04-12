from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

AlternativeConstructionObjective = Literal[
    "REDUCE_CONCENTRATION",
    "IMPROVE_RISK_ALIGNMENT",
    "RAISE_CASH",
    "LOWER_TURNOVER",
    "IMPROVE_CURRENCY_ALIGNMENT",
    "REBALANCE_TO_REFERENCE_MODEL",
    "AVOID_RESTRICTED_PRODUCTS",
    "MINIMIZE_APPROVAL_REQUIREMENTS",
    "PRESERVE_CLIENT_PREFERENCES",
    "LOWER_COST_AND_FRICTION",
]

AlternativeEvidenceRequirement = Literal[
    "RESTRICTED_PRODUCT_ELIGIBILITY",
    "MANDATE_CONTEXT",
    "CLIENT_PREFERENCES",
]

AlternativeCandidateStatus = Literal[
    "PROVISIONAL",
    "READY_FOR_SIMULATION",
]

AlternativeStatus = Literal[
    "FEASIBLE",
    "FEASIBLE_WITH_REVIEW",
    "REJECTED_CONSTRAINT_VIOLATION",
    "REJECTED_INSUFFICIENT_EVIDENCE",
    "REJECTED_SIMULATION_FAILED",
    "REJECTED_RISK_EVIDENCE_UNAVAILABLE",
    "REJECTED_POLICY_BLOCKED",
]


def _is_python_float(value: object) -> bool:
    return type(value) is type(0.1)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


class AlternativeMoneyConstraint(BaseModel):
    amount: Decimal = Field(
        description="Positive monetary amount used by alternatives constraints.",
        examples=["25000"],
    )
    currency: str = Field(
        description="ISO currency code used by the monetary constraint.",
        examples=["USD"],
    )

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float_amount(cls, value: object) -> object:
        if _is_python_float(value):
            raise ValueError(
                "ALTERNATIVES_INVALID_CONSTRAINT: amount must be provided as a decimal string"
            )
        return value

    @field_validator("amount")
    @classmethod
    def require_positive_amount(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("ALTERNATIVES_INVALID_CONSTRAINT: amount must be greater than 0")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ALTERNATIVES_INVALID_CONSTRAINT: currency is required")
        return normalized


class ProposalAlternativesConstraints(BaseModel):
    cash_floor: AlternativeMoneyConstraint | None = Field(
        default=None,
        description="Minimum cash floor that must remain after the alternative is applied.",
    )
    max_turnover_pct: Decimal | None = Field(
        default=None,
        description="Maximum permitted portfolio turnover percentage.",
        examples=["12.50"],
    )
    max_trade_count: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of generated trades allowed for the alternative.",
    )
    preserve_holdings: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that must remain held.",
    )
    restricted_instruments: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that must not appear in the alternative.",
    )
    do_not_buy: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that the strategy must not buy.",
    )
    do_not_sell: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that the strategy must not sell.",
    )
    allow_fx: bool = Field(
        default=True,
        description="Whether FX actions are permitted for the alternative.",
    )
    allowed_currencies: list[str] = Field(
        default_factory=list,
        description="Explicitly allowed target currencies when FX is permitted.",
    )
    mandate_restrictions: dict[str, Any] | None = Field(
        default=None,
        description="Optional mandate restrictions context for alternatives evaluation.",
    )
    client_preferences: dict[str, Any] | None = Field(
        default=None,
        description="Optional client preference context for alternatives evaluation.",
    )

    @field_validator("max_turnover_pct", mode="before")
    @classmethod
    def reject_float_turnover(cls, value: object) -> object:
        if _is_python_float(value):
            raise ValueError(
                "ALTERNATIVES_INVALID_CONSTRAINT: max_turnover_pct must be a decimal string"
            )
        return value

    @field_validator("max_turnover_pct")
    @classmethod
    def validate_turnover_range(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value < Decimal("0") or value > Decimal("100"):
            raise ValueError(
                "ALTERNATIVES_INVALID_CONSTRAINT: max_turnover_pct must be between 0 and 100"
            )
        return value

    @field_validator(
        "preserve_holdings",
        "restricted_instruments",
        "do_not_buy",
        "do_not_sell",
        mode="before",
    )
    @classmethod
    def normalize_instrument_lists(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip() for item in value])

    @field_validator("allowed_currencies", mode="before")
    @classmethod
    def normalize_currency_list(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip().upper() for item in value])


class ProposalAlternativesRequest(BaseModel):
    enabled: bool = Field(
        default=True,
        description="Whether alternatives generation is requested for this evaluation flow.",
    )
    objectives: list[AlternativeConstructionObjective] = Field(
        default_factory=list,
        description="Explicit advisor-requested construction objectives in priority order.",
    )
    constraints: ProposalAlternativesConstraints = Field(
        default_factory=ProposalAlternativesConstraints,
        description="Constraints that govern alternatives generation.",
    )
    max_alternatives: int = Field(
        default=3,
        ge=1,
        description="Maximum number of ranked alternatives to return.",
    )
    candidate_generation_policy_id: str | None = Field(
        default=None,
        description="Optional policy identifier controlling candidate generation behavior.",
    )
    ranking_policy_id: str | None = Field(
        default=None,
        description="Optional policy identifier controlling alternatives ranking behavior.",
    )
    include_rejected_candidates: bool = Field(
        default=True,
        description="Whether rejected alternatives should be retained in the response.",
    )
    evidence_requirements: list[AlternativeEvidenceRequirement] = Field(
        default_factory=list,
        description="Explicit upstream evidence requirements declared for this request.",
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description=(
            "Backend-issued alternative id selected in a later lifecycle or workspace write."
        ),
    )

    @field_validator("objectives", mode="before")
    @classmethod
    def dedupe_objectives(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip().upper() for item in value])

    @field_validator("evidence_requirements", mode="before")
    @classmethod
    def dedupe_evidence_requirements(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip().upper() for item in value])


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
        description="Deterministic generated intents placeholder for later slices.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy metadata required for later simulation and ranking slices.",
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
