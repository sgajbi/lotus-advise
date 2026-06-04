from typing import Literal

ProposalMemoLifecycleStatus = Literal["DRAFT", "FINALIZED"]
ProposalMemoReviewAction = Literal["APPROVE_FOR_ADVISOR_USE", "REQUEST_CHANGES", "REJECT"]
ProposalMemoReportPackageStatus = Literal["RECORDED", "BLOCKED", "DEGRADED"]
ProposalMemoReportOutputFormat = Literal["pdf", "json"]
ProposalMemoCommentarySection = Literal[
    "EXECUTIVE_SUMMARY",
    "RECOMMENDATION_RATIONALE",
    "RISK_AND_CONCENTRATION",
    "SUITABILITY_AND_MANDATE",
    "MATERIAL_CHANGES",
    "ALTERNATIVES_CONSIDERED",
    "APPROVALS_AND_NEXT_STEPS",
    "LIMITATIONS_AND_DISCLOSURES",
]


__all__ = [
    "ProposalMemoCommentarySection",
    "ProposalMemoLifecycleStatus",
    "ProposalMemoReportOutputFormat",
    "ProposalMemoReportPackageStatus",
    "ProposalMemoReviewAction",
]
