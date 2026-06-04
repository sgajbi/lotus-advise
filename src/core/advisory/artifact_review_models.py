from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.suitability_models import SuitabilityIssue


class ProposalArtifactSuitabilityHighlight(BaseModel):
    code: Literal["NEW", "RESOLVED", "PERSISTENT"] = Field(
        description="Suitability status-change highlight code.",
        examples=["NEW"],
    )
    text: str = Field(
        description="Deterministic suitability highlight text for presentation.",
        examples=["New issue: SUIT_ISSUER_MAX."],
    )


class ProposalArtifactSuitabilitySummary(BaseModel):
    status: Literal["AVAILABLE", "NOT_AVAILABLE"] = Field(
        description="Suitability section availability.",
        examples=["AVAILABLE"],
    )
    new_issues: int = Field(description="Count of NEW suitability issues.", examples=[1])
    resolved_issues: int = Field(description="Count of RESOLVED suitability issues.", examples=[0])
    persistent_issues: int = Field(
        description="Count of PERSISTENT suitability issues.",
        examples=[2],
    )
    highest_severity_new: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(
        default=None,
        description="Highest severity among NEW issues when present.",
        examples=["HIGH"],
    )
    highlights: List[ProposalArtifactSuitabilityHighlight] = Field(
        default_factory=list,
        description="Deterministic suitability highlights.",
    )
    issues: List[SuitabilityIssue] = Field(
        default_factory=list,
        description="Detailed deterministic suitability issue list.",
    )


class ProposalArtifactRiskLens(BaseModel):
    status: Literal["AVAILABLE", "NOT_AVAILABLE"] = Field(
        description="Risk-lens section availability.",
        examples=["AVAILABLE"],
    )
    source_service: Optional[str] = Field(
        default=None,
        description="Risk authority used to produce the proposal risk lens.",
        examples=["lotus-risk"],
    )
    summary: str = Field(
        description="Business-language summary of before/after concentration posture.",
        examples=["Concentration increases modestly after the proposal and remains reviewable."],
    )
    highlights: List[str] = Field(
        default_factory=list,
        description="Compact deterministic risk highlights for advisor review.",
    )
