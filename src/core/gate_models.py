from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class GateReason(BaseModel):
    reason_code: str = Field(
        description="Stable workflow reason code.",
        examples=["HARD_RULE_FAIL:INSUFFICIENT_CASH"],
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Reason severity level used for deterministic ordering.",
        examples=["HIGH"],
    )
    source: Literal["RULE_ENGINE", "SUITABILITY", "DATA_QUALITY"] = Field(
        description="Reason source subsystem.",
        examples=["RULE_ENGINE"],
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic structured details for the reason.",
    )


class GateDecisionSummary(BaseModel):
    hard_fail_count: int = Field(description="Count of hard rule failures.", examples=[1])
    soft_fail_count: int = Field(description="Count of soft rule failures.", examples=[0])
    new_high_suitability_count: int = Field(
        description="Count of NEW suitability issues with HIGH severity.",
        examples=[0],
    )
    new_medium_suitability_count: int = Field(
        description="Count of NEW suitability issues with MEDIUM severity.",
        examples=[0],
    )


class GateDecision(BaseModel):
    gate: Literal[
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "CLIENT_CONSENT_REQUIRED",
        "EXECUTION_READY",
        "NONE",
    ] = Field(
        description="Deterministic workflow gate outcome.",
        examples=["CLIENT_CONSENT_REQUIRED"],
    )
    recommended_next_step: Literal[
        "FIX_INPUT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "REQUEST_CLIENT_CONSENT",
        "EXECUTE",
        "NONE",
    ] = Field(
        description="Recommended next workflow step based on gate policy.",
        examples=["REQUEST_CLIENT_CONSENT"],
    )
    reasons: List[GateReason] = Field(
        default_factory=list,
        description="Deterministic ordered reasons explaining the gate.",
    )
    summary: GateDecisionSummary = Field(description="Gate summary counters.")


__all__ = [
    "GateDecision",
    "GateDecisionSummary",
    "GateReason",
]
