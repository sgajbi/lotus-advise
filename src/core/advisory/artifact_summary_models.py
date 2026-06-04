from typing import List, Literal

from pydantic import BaseModel, Field


class ProposalArtifactSummaryNote(BaseModel):
    code: str = Field(description="Deterministic summary note code.", examples=["NOTE"])
    text: str = Field(
        description="Deterministic summary note text suitable for UI rendering.",
        examples=["Client requested partial risk increase and cash deployment."],
    )


class ProposalArtifactTakeaway(BaseModel):
    code: str = Field(description="Machine-readable takeaway code.", examples=["DRIFT"])
    value: str = Field(
        description="Deterministic takeaway statement derived from simulation data.",
        examples=["Asset-class drift reduced from 0.1200 to 0.0700."],
    )


class ProposalArtifactSummary(BaseModel):
    title: str = Field(
        description="Artifact title for advisor/client views.",
        examples=["Proposal for PB_SG_GLOBAL_BAL_001"],
    )
    objective_tags: List[str] = Field(
        default_factory=list,
        description="Deterministic objective tags derived from proposal inputs and outputs.",
        examples=[["DRIFT_REDUCTION", "RISK_ALIGNMENT", "CASH_DEPLOYMENT"]],
    )
    advisor_notes: List[ProposalArtifactSummaryNote] = Field(
        default_factory=list,
        description="Structured advisor notes derived from proposal evidence.",
    )
    recommended_next_step: Literal[
        "CLIENT_CONSENT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "EXECUTION_READY",
        "NONE",
    ] = Field(
        description="Deterministic post-simulation workflow recommendation.",
        examples=["CLIENT_CONSENT"],
    )
    key_takeaways: List[ProposalArtifactTakeaway] = Field(
        default_factory=list,
        description="Deterministic machine-derived proposal takeaways.",
    )
