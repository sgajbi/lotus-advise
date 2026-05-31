from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.models import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.validation import (
    normalize_rfc28_business_text,
)

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


def build_journey_integration_proof_summary(
    live_runtime_payload: dict[str, Any],
) -> AdvisoryJourneyIntegrationProofSummary:
    parity = _dict_at(live_runtime_payload, "parity")
    policy = _dict_at(parity, "proposal_policy")
    return AdvisoryJourneyIntegrationProofSummary(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        required_workbench_panels=[
            "advisory.advisor_cockpit",
            "advisory.suitability_review",
            "proposal.memo_evidence_pack",
            "advisory.bank_demo_proof",
        ],
        ai_model_risk_controls=[
            _narrative_ai_control(_dict_at(parity, "proposal_narrative")),
            _memo_ai_control(_dict_at(parity, "proposal_memo")),
            _policy_ai_control(policy),
            _copilot_ai_control(_optional_dict_at(parity, "advisory_copilot")),
        ],
        policy_evidence=PolicyEvidenceProof(
            proof_posture="IMPLEMENTATION_BACKED",
            policy_pack_id=str(_required_value_at(policy, "policy_pack_id")),
            policy_version=str(_required_value_at(policy, "policy_version")),
            evaluation_status=str(_required_value_at(policy, "evaluation_status")),
            material_rule_count=_int_at(policy, "material_rule_count"),
            pending_rule_count=_int_at(policy, "pending_rule_count"),
            workflow_sign_off_status=str(_required_value_at(policy, "workflow_sign_off_status")),
            client_ready_publication=str(
                _required_value_at(policy, "workflow_client_ready_publication")
            ),
        ),
        cockpit_evidence=CockpitEvidenceProof(
            proof_posture=(
                "IMPLEMENTATION_BACKED"
                if _optional_dict_at(parity, "advisor_cockpit")
                else "REVIEW_REQUIRED"
            ),
            client_ready_publication="BLOCKED",
        ),
        unsupported_claims=[
            "AI is not authoritative for advice, approval, policy sign-off, or publication.",
            (
                "Underlying AI inputs, model outputs, and source evidence are excluded "
                "from shared proof summaries."
            ),
            (
                "Advisor acknowledgements do not clear policy blockers or client-ready "
                "publication gates."
            ),
            "Client-ready publication and external client communication remain blocked.",
        ],
    )


def _narrative_ai_control(snapshot: dict[str, Any]) -> AiModelRiskControlProof:
    ai_status = str(_required_value_at(snapshot, "ai_assisted_status"))
    return AiModelRiskControlProof(
        evidence_family="PROPOSAL_NARRATIVE",
        proof_posture="IMPLEMENTATION_BACKED",
        ai_status=ai_status,
        authoritative_for_advice=False,
        human_review_required=True,
        raw_prompt_retained=False,
        raw_source_evidence_included=False,
        guardrail_status=str(_required_value_at(snapshot, "guardrail_failure_status")),
        lineage_complete=None,
    )


def _memo_ai_control(snapshot: dict[str, Any]) -> AiModelRiskControlProof:
    return AiModelRiskControlProof(
        evidence_family="PROPOSAL_MEMO",
        proof_posture="IMPLEMENTATION_BACKED",
        ai_status=str(_required_value_at(snapshot, "ai_status")),
        authoritative_for_advice=_bool_at(snapshot, "ai_authoritative_for_memo_status"),
        human_review_required=_bool_at(snapshot, "ai_review_required"),
        raw_prompt_retained=False,
        raw_source_evidence_included=False,
        guardrail_status=str(_required_value_at(snapshot, "client_ready_release_block_status")),
        lineage_complete=_bool_at(snapshot, "lineage_complete"),
    )


def _policy_ai_control(snapshot: dict[str, Any]) -> AiModelRiskControlProof:
    return AiModelRiskControlProof(
        evidence_family="POLICY_EVIDENCE",
        proof_posture="IMPLEMENTATION_BACKED",
        ai_status=str(_required_value_at(snapshot, "ai_status")),
        authoritative_for_advice=_bool_at(snapshot, "ai_authoritative_for_policy_status"),
        human_review_required=_bool_at(snapshot, "ai_human_review_required"),
        raw_prompt_retained=False,
        raw_source_evidence_included=_bool_at(snapshot, "ai_raw_source_evidence_included"),
        guardrail_status=str(_required_value_at(snapshot, "forbidden_ai_action_block_status")),
        lineage_complete=_bool_at(snapshot, "lineage_complete"),
    )


def _copilot_ai_control(snapshot: dict[str, Any] | None) -> AiModelRiskControlProof:
    if snapshot is None:
        return AiModelRiskControlProof(
            evidence_family="ADVISORY_COPILOT",
            proof_posture="NOT_PROBED",
            ai_status="NOT_IN_BACKEND_LIVE_RUNTIME_SUITE",
            authoritative_for_advice=False,
            human_review_required=True,
            raw_prompt_retained=False,
            raw_source_evidence_included=False,
            guardrail_status="WORKBENCH_OR_API_PROOF_REQUIRED_BEFORE_DEMO_PROMOTION",
            lineage_complete=None,
        )
    return AiModelRiskControlProof(
        evidence_family="ADVISORY_COPILOT",
        proof_posture="IMPLEMENTATION_BACKED",
        ai_status=str(_required_value_at(snapshot, "ai_status")),
        authoritative_for_advice=_bool_at(snapshot, "authoritative_for_advice"),
        human_review_required=_bool_at(snapshot, "human_review_required"),
        raw_prompt_retained=_bool_at(snapshot, "raw_prompt_retained"),
        raw_source_evidence_included=_bool_at(snapshot, "raw_source_evidence_included"),
        guardrail_status=str(_required_value_at(snapshot, "guardrail_status")),
        lineage_complete=_bool_at(snapshot, "lineage_complete"),
    )


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"RFC0028_INTEGRATION_PROOF_FIELD_MISSING: {key}")
    return value


def _optional_dict_at(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"RFC0028_INTEGRATION_PROOF_FIELD_INVALID: {key}")
    return value


def _required_value_at(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise ValueError(f"RFC0028_INTEGRATION_PROOF_FIELD_MISSING: {key}")
    return payload[key]


def _bool_at(payload: dict[str, Any], key: str) -> bool:
    value = _required_value_at(payload, key)
    if not isinstance(value, bool):
        raise ValueError(f"RFC0028_INTEGRATION_PROOF_FIELD_INVALID: {key}")
    return value


def _int_at(payload: dict[str, Any], key: str) -> int:
    value = _required_value_at(payload, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"RFC0028_INTEGRATION_PROOF_FIELD_INVALID: {key}")
    return value


def _normalize_status_text(
    value: str,
    *,
    field_name: str,
    max_length: int = _RFC28_INTEGRATION_IDENTIFIER_MAX_LENGTH,
) -> str:
    return normalize_rfc28_business_text(
        value,
        field_name=field_name,
        max_length=max_length,
    )
