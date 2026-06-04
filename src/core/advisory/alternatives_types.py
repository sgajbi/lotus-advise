from typing import Literal

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


__all__ = [
    "AlternativeCandidateStatus",
    "AlternativeConstructionObjective",
    "AlternativeEvidenceRequirement",
    "AlternativeStatus",
]
