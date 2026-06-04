from __future__ import annotations

from typing import Any

from src.core.bank_demo_proof.integration_proof_models import (
    AdvisoryJourneyIntegrationProofSummary as AdvisoryJourneyIntegrationProofSummary,
)
from src.core.bank_demo_proof.integration_proof_models import (
    AiEvidenceFamily as AiEvidenceFamily,
)
from src.core.bank_demo_proof.integration_proof_models import (
    AiModelRiskControlProof as AiModelRiskControlProof,
)
from src.core.bank_demo_proof.integration_proof_models import (
    CockpitEvidenceProof as CockpitEvidenceProof,
)
from src.core.bank_demo_proof.integration_proof_models import (
    IntegrationProofPosture as IntegrationProofPosture,
)
from src.core.bank_demo_proof.integration_proof_models import (
    PolicyEvidenceProof as PolicyEvidenceProof,
)
from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)


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
