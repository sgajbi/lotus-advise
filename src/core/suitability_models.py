from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SuitabilityEvidenceSnapshotIds(BaseModel):
    portfolio_snapshot_id: str = Field(
        description="Portfolio snapshot id used as evidence source.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    market_data_snapshot_id: str = Field(
        description="Market-data snapshot id used as evidence source.",
        examples=["md_2026_02_19"],
    )


class SuitabilityEvidence(BaseModel):
    as_of: str = Field(
        description="Suitability evidence as-of identifier derived from request snapshots.",
        examples=["md_2026_02_19"],
    )
    snapshot_ids: SuitabilityEvidenceSnapshotIds = Field(
        description="Snapshot identifiers used by suitability checks."
    )


class SuitabilityIssue(BaseModel):
    issue_id: str = Field(
        description="Stable suitability issue identifier.",
        examples=["SUIT_SINGLE_POSITION_MAX"],
    )
    issue_key: str = Field(
        description="Deterministic issue key used for before/after classification.",
        examples=["SINGLE_POSITION_MAX|US_EQ_ETF"],
    )
    dimension: Literal[
        "CONCENTRATION",
        "ISSUER",
        "LIQUIDITY",
        "GOVERNANCE",
        "PRODUCT",
        "CASH",
        "DATA_QUALITY",
    ] = Field(
        description="Suitability issue dimension.",
        examples=["CONCENTRATION"],
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Advisory suitability severity level.",
        examples=["HIGH"],
    )
    status_change: Literal["NEW", "RESOLVED", "PERSISTENT"] = Field(
        description="Before/after suitability state transition class.",
        examples=["NEW"],
    )
    classification: Literal[
        "NEW",
        "RESOLVED",
        "PERSISTENT",
        "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
    ] = Field(
        description="Enterprise suitability classification used by decision policy.",
        examples=["UNKNOWN_DUE_TO_MISSING_EVIDENCE"],
    )
    summary: str = Field(
        description="Short suitability issue narrative.",
        examples=["Single position exceeds 10% cap."],
    )
    remediation: Optional[str] = Field(
        default=None,
        description="Deterministic advisor remediation guidance for the issue.",
        examples=["Capture client knowledge and experience evidence before proceeding."],
    )
    approval_implication: Optional[str] = Field(
        default=None,
        description="Approval or review implication triggered by this issue.",
        examples=["COMPLIANCE_REVIEW"],
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic suitability measurement details encoded as strings.",
        examples=[
            {
                "threshold": "0.10",
                "measured_before": "0.12",
                "measured_after": "0.09",
                "instrument_id": "US_EQ_ETF",
            }
        ],
    )
    evidence: SuitabilityEvidence = Field(description="Evidence lineage for this issue.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Suitability policy-pack identifier that produced the issue.",
        examples=["global-private-banking-baseline"],
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Suitability policy version that produced the issue.",
        examples=["enterprise-suitability-policy.2026-04"],
    )


class SuitabilitySummary(BaseModel):
    new_count: int = Field(description="Count of NEW suitability issues.", examples=[1])
    resolved_count: int = Field(description="Count of RESOLVED suitability issues.", examples=[2])
    persistent_count: int = Field(
        description="Count of PERSISTENT suitability issues.",
        examples=[3],
    )
    highest_severity_new: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(
        default=None,
        description="Highest severity among NEW issues, when present.",
        examples=["HIGH"],
    )


class SuitabilityResult(BaseModel):
    summary: SuitabilitySummary = Field(description="Suitability issue summary counts.")
    issues: List[SuitabilityIssue] = Field(
        default_factory=list,
        description="Deterministic ordered suitability issue list.",
    )
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Suitability policy-pack identifier used for this evaluation.",
        examples=["global-private-banking-baseline"],
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Suitability policy version used for this evaluation.",
        examples=["enterprise-suitability-policy.2026-04"],
    )
    recommended_gate: Literal["NONE", "RISK_REVIEW", "COMPLIANCE_REVIEW"] = Field(
        description="Advisory gate recommendation derived from NEW issue severities.",
        examples=["COMPLIANCE_REVIEW"],
    )


__all__ = [
    "SuitabilityEvidence",
    "SuitabilityEvidenceSnapshotIds",
    "SuitabilityIssue",
    "SuitabilityResult",
    "SuitabilitySummary",
]
