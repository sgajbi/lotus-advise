from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.policy_packs.catalog_models import PolicyPackSummary

PolicyEvaluationStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED", "NOT_APPLICABLE"]
PolicyApplicabilityStatus = Literal["APPLICABLE", "NOT_APPLICABLE", "BLOCKED"]


class PolicyPackApplicabilityResult(BaseModel):
    status: PolicyApplicabilityStatus = Field(
        description="Whether this policy pack applies to the proposal evidence.",
        examples=["APPLICABLE"],
    )
    matched_selectors: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Applicability selectors matched from source-owned proposal evidence, including "
            "jurisdiction, booking center, legal entity, client segment, and product scope where "
            "declared by the policy pack."
        ),
        examples=[
            {
                "jurisdiction": "SG",
                "booking_center_code": "SG",
                "legal_entity_code": "REFERENCE",
                "client_segment": "ACCREDITED_INVESTOR",
                "product_scope": "MULTI_ASSET",
            }
        ],
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Source-owned selector evidence missing before applicability can be decided.",
        examples=[["jurisdiction"]],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Domain reason codes explaining applicability posture.",
        examples=[["POLICY_PACK_APPLIES_TO_PROPOSAL_CONTEXT"]],
    )


class PolicyRuleEvaluationResult(BaseModel):
    rule_id: str = Field(description="Policy-pack rule identifier.")
    status: PolicyEvaluationStatus = Field(
        description="Rule evaluation posture for this proposal evidence.",
        examples=["PENDING_REVIEW"],
    )
    severity: str = Field(description="Policy-pack rule severity.", examples=["BLOCKING"])
    outcome: str = Field(
        description="Domain outcome for the evaluated rule; never a generic pass/fail claim.",
        examples=["DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED"],
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Concrete proposal evidence references used by this result.",
    )
    source_authority_refs: list[str] = Field(
        default_factory=list,
        description="Source-owner references backing the rule result.",
        examples=[["lotus-core:core_product_eligibility_target_market_complexity"]],
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Missing evidence that prevents a positive policy outcome.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining rule status.",
    )
    required_actions: list[str] = Field(
        default_factory=list,
        description="Advisor, policy, compliance, or supervisory actions required by the rule.",
    )


class PolicyPackEvaluationResponse(BaseModel):
    contract_version: str = Field(
        description="Internal RFC-0025 policy evaluation engine contract version.",
        examples=["rfc0025.policy-evaluation-engine.v1"],
    )
    policy_pack: PolicyPackSummary = Field(description="Evaluated active policy pack.")
    evaluation_status: PolicyEvaluationStatus = Field(
        description="Aggregate evaluation posture across applicable rules.",
        examples=["PENDING_REVIEW"],
    )
    applicability: PolicyPackApplicabilityResult = Field(
        description="Source-backed applicability result for the policy pack."
    )
    source_posture: dict[str, Any] = Field(
        description="Policy source-readiness posture consumed by the evaluator.",
        examples=[{"contract_version": "rfc0025.policy-source-readiness.v1"}],
    )
    rule_results: list[PolicyRuleEvaluationResult] = Field(
        description="Material rule results with source refs, gaps, reasons, and required actions."
    )
    supportability: dict[str, Any] = Field(
        description="Current support boundary for the internal policy evaluation engine.",
        examples=[{"policy_evaluation_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"}],
    )
