from typing import Literal

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
]
