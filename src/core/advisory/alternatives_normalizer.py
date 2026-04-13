from typing import Literal

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import (
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
    ProposalAlternativesConstraints,
    ProposalAlternativesRequest,
)

FIRST_IMPLEMENTATION_MAX_ALTERNATIVES = 3
FIRST_IMPLEMENTATION_OBJECTIVES: tuple[AlternativeConstructionObjective, ...] = (
    "REDUCE_CONCENTRATION",
    "RAISE_CASH",
    "LOWER_TURNOVER",
    "IMPROVE_CURRENCY_ALIGNMENT",
)
CONDITIONAL_OBJECTIVES: tuple[AlternativeConstructionObjective, ...] = (
    "AVOID_RESTRICTED_PRODUCTS",
)
DEFERRED_OBJECTIVES: tuple[AlternativeConstructionObjective, ...] = (
    "IMPROVE_RISK_ALIGNMENT",
    "REBALANCE_TO_REFERENCE_MODEL",
    "MINIMIZE_APPROVAL_REQUIREMENTS",
    "PRESERVE_CLIENT_PREFERENCES",
    "LOWER_COST_AND_FRICTION",
)


class AlternativesRequestNormalizationError(ValueError):
    def __init__(self, *, reason_code: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or {}


class NormalizedProposalAlternativesRequest(BaseModel):
    requested_objectives: tuple[AlternativeConstructionObjective, ...] = Field(
        description="Deterministic normalized objective order for alternatives generation."
    )
    constraints: ProposalAlternativesConstraints = Field(
        description="Normalized alternatives constraints payload."
    )
    max_alternatives: int = Field(
        description="Normalized maximum number of ranked alternatives to return."
    )
    candidate_generation_policy_id: str | None = Field(
        default=None,
        description="Optional candidate-generation policy identifier.",
    )
    ranking_policy_id: str | None = Field(
        default=None,
        description="Optional ranking policy identifier.",
    )
    include_rejected_candidates: bool = Field(
        description="Whether rejected alternatives should remain visible downstream."
    )
    evidence_requirements: tuple[AlternativeEvidenceRequirement, ...] = Field(
        default=(),
        description="Normalized upstream evidence requirements declared for this request.",
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Backend-issued selected alternative id for selection-mode writes.",
    )
    missing_evidence_reason_codes: tuple[str, ...] = Field(
        default=(),
        description="Deterministic missing-evidence reason codes inferred from the request.",
    )


def normalize_alternatives_request(
    request: ProposalAlternativesRequest | None,
    *,
    selection_mode: Literal["generation", "selection"] = "generation",
) -> NormalizedProposalAlternativesRequest | None:
    if request is None or request.enabled is False:
        return None
    if not request.objectives:
        raise AlternativesRequestNormalizationError(
            reason_code="ALTERNATIVES_OBJECTIVES_REQUIRED",
            message=(
                "At least one alternatives objective is required when alternatives are enabled."
            ),
        )
    if request.max_alternatives > FIRST_IMPLEMENTATION_MAX_ALTERNATIVES:
        raise AlternativesRequestNormalizationError(
            reason_code="ALTERNATIVES_MAX_LIMIT_EXCEEDED",
            message=(
                "First implementation alternatives are bounded to a maximum of "
                f"{FIRST_IMPLEMENTATION_MAX_ALTERNATIVES} ranked alternatives."
            ),
            details={"max_alternatives": request.max_alternatives},
        )
    if selection_mode == "generation" and request.selected_alternative_id is not None:
        raise AlternativesRequestNormalizationError(
            reason_code="ALTERNATIVES_SELECTION_NOT_ALLOWED_ON_GENERATION",
            message=(
                "selected_alternative_id is only valid on lifecycle or workspace selection writes, "
                "not on first-time generation requests."
            ),
        )
    deferred_objectives = [
        objective for objective in request.objectives if objective in DEFERRED_OBJECTIVES
    ]
    if deferred_objectives:
        raise AlternativesRequestNormalizationError(
            reason_code="ALTERNATIVES_OBJECTIVE_NOT_SUPPORTED",
            message="One or more requested alternatives objectives are explicitly deferred.",
            details={"deferred_objectives": deferred_objectives},
        )
    missing_evidence_reason_codes = _infer_missing_evidence_reason_codes(request)
    return NormalizedProposalAlternativesRequest(
        requested_objectives=tuple(request.objectives),
        constraints=request.constraints,
        max_alternatives=request.max_alternatives,
        candidate_generation_policy_id=request.candidate_generation_policy_id,
        ranking_policy_id=request.ranking_policy_id,
        include_rejected_candidates=request.include_rejected_candidates,
        evidence_requirements=tuple(request.evidence_requirements),
        selected_alternative_id=request.selected_alternative_id,
        missing_evidence_reason_codes=tuple(missing_evidence_reason_codes),
    )


def _infer_missing_evidence_reason_codes(
    request: ProposalAlternativesRequest,
) -> list[str]:
    declared = set(request.evidence_requirements)
    missing: list[str] = []
    if (
        "AVOID_RESTRICTED_PRODUCTS" in request.objectives
        and "RESTRICTED_PRODUCT_ELIGIBILITY" not in declared
    ):
        missing.append("MISSING_RESTRICTED_PRODUCT_ELIGIBILITY")
    if request.constraints.mandate_restrictions and "MANDATE_CONTEXT" not in declared:
        missing.append("MISSING_MANDATE_CONTEXT")
    if request.constraints.client_preferences and "CLIENT_PREFERENCES" not in declared:
        missing.append("MISSING_CLIENT_PREFERENCES")
    return missing
