from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.validation import normalize_rfc28_business_text

IntegrationProofPosture = Literal[
    "IMPLEMENTATION_BACKED",
    "REVIEW_REQUIRED",
    "BLOCKED",
    "NOT_PROBED",
]
AiEvidenceFamily = Literal[
    "PROPOSAL_NARRATIVE",
    "PROPOSAL_MEMO",
    "POLICY_EVIDENCE",
    "ADVISORY_COPILOT",
]
_RFC28_INTEGRATION_IDENTIFIER_MAX_LENGTH = 160
_RFC28_INTEGRATION_TEXT_MAX_LENGTH = 1000
_RFC28_INTEGRATION_PANEL_MAX_ITEMS = 16
_RFC28_INTEGRATION_AI_ROW_MAX_ITEMS = 16
_RFC28_INTEGRATION_UNSUPPORTED_MAX_ITEMS = 32
_RFC28_POLICY_RULE_COUNT_MAX = 100_000


class AiModelRiskControlProof(BaseModel):
    evidence_family: AiEvidenceFamily = Field(
        description="Advisory evidence family covered by this AI/model-risk proof row."
    )
    proof_posture: IntegrationProofPosture = Field(
        description="Bounded implementation posture for this proof row."
    )
    ai_status: str = Field(description="Source-owned AI or workflow-pack posture.")
    authoritative_for_advice: bool = Field(
        description="Whether AI is allowed to be the authority for advice or approval."
    )
    human_review_required: bool = Field(
        description="Whether human review is required before advisor-use reliance."
    )
    raw_prompt_retained: bool = Field(
        description="Whether unredacted AI input or output material is retained in the proof pack."
    )
    raw_source_evidence_included: bool = Field(
        description="Whether unredacted source evidence is included in the AI proof payload."
    )
    guardrail_status: str = Field(
        description="Bounded guardrail, unavailable, or forbidden-action posture."
    )
    lineage_complete: bool | None = Field(
        default=None,
        description="Whether source-owned AI lineage is complete when the source exposes it.",
    )

    @field_validator("ai_status", "guardrail_status")
    @classmethod
    def _ai_status_fields_must_be_bounded(cls, value: str) -> str:
        return _normalize_status_text(value, field_name="AI proof status")

    @model_validator(mode="after")
    def _ai_cannot_be_authoritative_or_leak_raw_material(
        self,
    ) -> AiModelRiskControlProof:
        if self.authoritative_for_advice:
            raise ValueError("AI proof cannot be authoritative for advice or approval")
        if self.raw_prompt_retained or self.raw_source_evidence_included:
            raise ValueError("AI proof summary cannot retain unredacted AI/source material")
        if self.proof_posture == "IMPLEMENTATION_BACKED" and not self.human_review_required:
            raise ValueError("implementation-backed AI proof requires human review posture")
        return self


class PolicyEvidenceProof(BaseModel):
    proof_posture: IntegrationProofPosture = Field(
        description="Bounded policy evidence integration posture."
    )
    policy_pack_id: str = Field(description="Source-owned policy pack identifier.")
    policy_version: str = Field(description="Source-owned policy pack version.")
    evaluation_status: str = Field(description="Source-owned policy evaluation status.")
    material_rule_count: int = Field(
        ge=0,
        le=_RFC28_POLICY_RULE_COUNT_MAX,
        description="Number of material rules evaluated.",
    )
    pending_rule_count: int = Field(
        ge=0,
        le=_RFC28_POLICY_RULE_COUNT_MAX,
        description="Rules still requiring advisor or compliance review.",
    )
    workflow_sign_off_status: str = Field(description="Source-owned sign-off workflow posture.")
    client_ready_publication: Literal["BLOCKED"] = Field(
        description="Client-ready publication posture for policy evidence."
    )
    legal_advice_claimed: bool = Field(
        default=False,
        description="Whether the proof row claims legal or regulatory advice.",
    )

    @field_validator(
        "policy_pack_id",
        "policy_version",
        "evaluation_status",
        "workflow_sign_off_status",
    )
    @classmethod
    def _policy_status_fields_must_be_bounded(cls, value: str) -> str:
        return _normalize_status_text(value, field_name="policy proof status")

    @model_validator(mode="after")
    def _policy_proof_cannot_overclaim(self) -> PolicyEvidenceProof:
        if self.pending_rule_count > self.material_rule_count:
            raise ValueError("policy proof pending rule count cannot exceed material rule count")
        if self.client_ready_publication != "BLOCKED":
            raise ValueError("policy proof must keep client-ready publication blocked")
        if self.legal_advice_claimed:
            raise ValueError("policy proof cannot claim legal or regulatory advice")
        return self


class CockpitEvidenceProof(BaseModel):
    proof_posture: IntegrationProofPosture = Field(
        description="Bounded advisor-cockpit integration posture."
    )
    required_workbench_panel: Literal["advisory.advisor_cockpit"] = Field(
        default="advisory.advisor_cockpit",
        description="Governed Workbench panel required for cockpit product proof.",
    )
    source_authority: Literal["lotus-advise"] = Field(default="lotus-advise")
    client_ready_publication: Literal["BLOCKED"] = Field(
        description="Client-ready publication posture for cockpit actions."
    )
    local_workflow_logic_allowed: bool = Field(
        default=False,
        description="Whether Gateway or Workbench may reconstruct cockpit workflow logic.",
    )
    acknowledgement_clears_policy_blockers: bool = Field(
        default=False,
        description="Whether advisor acknowledgement is allowed to clear policy blockers.",
    )

    @model_validator(mode="after")
    def _cockpit_boundary_must_remain_source_owned(self) -> CockpitEvidenceProof:
        if self.local_workflow_logic_allowed:
            raise ValueError("cockpit proof cannot allow local workflow reconstruction")
        if self.acknowledgement_clears_policy_blockers:
            raise ValueError("cockpit acknowledgement cannot clear policy blockers")
        if self.client_ready_publication != "BLOCKED":
            raise ValueError("cockpit proof must keep client-ready publication blocked")
        return self


class AdvisoryJourneyIntegrationProofSummary(BaseModel):
    contract_name: Literal["AdvisoryJourneyIntegrationProofSummary"] = Field(
        default="AdvisoryJourneyIntegrationProofSummary"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(description="RFC-0028 scenario identifier.")
    primary_portfolio_id: str = Field(description="Canonical portfolio identifier.")
    proof_marker: str = Field(description="RFC-0028 proof marker.")
    required_workbench_panels: list[str] = Field(
        min_length=1,
        max_length=_RFC28_INTEGRATION_PANEL_MAX_ITEMS,
        description=(
            "Governed Workbench panels required before product-surface claims are promoted."
        ),
    )
    ai_model_risk_controls: list[AiModelRiskControlProof] = Field(
        min_length=1,
        max_length=_RFC28_INTEGRATION_AI_ROW_MAX_ITEMS,
        description="AI and model-risk control proof rows for the shown advisory evidence.",
    )
    policy_evidence: PolicyEvidenceProof = Field(
        description="Policy-pack and sign-off evidence proof posture."
    )
    cockpit_evidence: CockpitEvidenceProof = Field(
        description="Advisor cockpit product-proof boundary posture."
    )
    unsupported_claims: list[str] = Field(
        min_length=1,
        max_length=_RFC28_INTEGRATION_UNSUPPORTED_MAX_ITEMS,
        description="Claims blocked by the integration proof summary.",
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _summary_identifiers_must_be_bounded(cls, value: str) -> str:
        return _normalize_status_text(value, field_name="integration proof identifier")

    @field_validator("required_workbench_panels")
    @classmethod
    def _required_panels_must_be_bounded(cls, value: list[str]) -> list[str]:
        normalized = [
            _normalize_status_text(panel, field_name="required workbench panel") for panel in value
        ]
        if len(set(normalized)) != len(normalized):
            raise ValueError("integration proof required Workbench panels must be unique")
        return normalized

    @field_validator("unsupported_claims")
    @classmethod
    def _unsupported_claims_must_be_business_safe(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for claim in value:
            claim_text = normalize_rfc28_business_text(
                claim,
                field_name="integration proof unsupported claim",
                max_length=_RFC28_INTEGRATION_TEXT_MAX_LENGTH,
            )
            normalized.append(claim_text)
        return normalized

    @model_validator(mode="after")
    def _integration_summary_must_include_governed_panels(
        self,
    ) -> AdvisoryJourneyIntegrationProofSummary:
        required = {
            "advisory.advisor_cockpit",
            "advisory.suitability_review",
            "proposal.memo_evidence_pack",
            "advisory.bank_demo_proof",
        }
        missing = required.difference(self.required_workbench_panels)
        if missing:
            raise ValueError(f"integration proof missing Workbench panels: {sorted(missing)}")
        return self


def _normalize_status_text(
    value: str,
    *,
    field_name: str,
    max_length: int = _RFC28_INTEGRATION_IDENTIFIER_MAX_LENGTH,
) -> str:
    return cast(
        str,
        normalize_rfc28_business_text(
            value,
            field_name=field_name,
            max_length=max_length,
        ),
    )


__all__ = [
    "AdvisoryJourneyIntegrationProofSummary",
    "AiEvidenceFamily",
    "AiModelRiskControlProof",
    "CockpitEvidenceProof",
    "IntegrationProofPosture",
    "PolicyEvidenceProof",
]
