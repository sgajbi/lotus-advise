from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx

from src.core.advisory_copilot import (
    CopilotAudience,
    CopilotEvidencePacket,
    CopilotGuardrailReasonCode,
    CopilotLineageRef,
    CopilotSourceRef,
    align_copilot_output_claims_to_evidence,
    evaluate_copilot_guardrails,
    workflow_pack_id_for_action,
    workflow_pack_version_for_action,
)
from src.core.advisory_copilot.evaluation_gate import (
    AdvisoryCopilotEvaluationResult,
    evaluate_advisory_copilot_model_risk,
)
from src.core.advisory_copilot.model_governance import (
    ADVISORY_COPILOT_APPROVED_INSTRUCTION_SET,
    ADVISORY_COPILOT_EVALUATION_PACK_REF,
    ADVISORY_COPILOT_OUTPUT_SCHEMA_VERSION,
    ADVISORY_COPILOT_PROMPT_TEMPLATE_VERSION,
    AdvisoryCopilotModelApproval,
    advisory_copilot_model_approval_for_request,
    validate_advisory_copilot_model_response,
)
from src.integrations.lotus_ai.advisory_copilot_request import (
    build_advisory_copilot_workflow_pack_request,
    has_source_refs,
    workflow_surface,
)
from src.integrations.lotus_ai.output_safety import (
    DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH,
    DEFAULT_AI_OUTPUT_SECTION_LIMIT,
    DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH,
    DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH,
    DEFAULT_AI_REVIEW_GUIDANCE_LENGTH,
    DEFAULT_AI_REVIEW_GUIDANCE_LIMIT,
    map_bounded_string_list,
    map_review_required_sections,
)
from src.integrations.lotus_ai.runtime_config import resolve_lotus_ai_base_url
from src.integrations.lotus_ai.workflow_request import workflow_pack_environment
from src.integrations.lotus_ai.workflow_response import (
    extract_error_detail,
    extract_model_version,
    extract_provider_id,
    extract_workflow_run_id,
    safe_dict,
)
from src.integrations.lotus_core.runtime_config import env_positive_float

ADAPTER_VERSION = "advisory-copilot-lotus-ai-adapter.v1"
APPROVED_INSTRUCTION_SET = ADVISORY_COPILOT_APPROVED_INSTRUCTION_SET
PROMPT_TEMPLATE_VERSION = ADVISORY_COPILOT_PROMPT_TEMPLATE_VERSION
OUTPUT_SCHEMA_VERSION = ADVISORY_COPILOT_OUTPUT_SCHEMA_VERSION
EVALUATION_PACK_REF = ADVISORY_COPILOT_EVALUATION_PACK_REF
MAX_COPILOT_OUTPUT_SECTIONS = DEFAULT_AI_OUTPUT_SECTION_LIMIT
MAX_COPILOT_SECTION_KEY_LENGTH = DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH
MAX_COPILOT_SECTION_TITLE_LENGTH = DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH
MAX_COPILOT_SECTION_TEXT_LENGTH = DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH
MAX_COPILOT_REVIEW_GUIDANCE_ITEMS = DEFAULT_AI_REVIEW_GUIDANCE_LIMIT
MAX_COPILOT_REVIEW_GUIDANCE_LENGTH = DEFAULT_AI_REVIEW_GUIDANCE_LENGTH
MAX_COPILOT_LINEAGE_REF_LENGTH = 160


@dataclass(frozen=True)
class AdvisoryCopilotAiDraft:
    status: str
    sections: tuple[dict[str, Any], ...]
    lineage: dict[str, Any]
    review_guidance: tuple[str, ...]
    guardrail_reasons: tuple[CopilotGuardrailReasonCode, ...]


def generate_advisory_copilot_draft_with_lotus_ai(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: list[str],
    requested_by: str,
    reason: dict[str, Any],
    requested_intents: tuple[str, ...] = (),
    user_instruction: str = "",
) -> AdvisoryCopilotAiDraft:
    preflight_rejection = _preflight_guardrail_rejection(
        evidence_packet=evidence_packet,
        requested_intents=requested_intents,
        user_instruction=user_instruction,
    )
    if preflight_rejection is not None:
        return preflight_rejection

    environment = workflow_pack_environment()
    approval_decision = advisory_copilot_model_approval_for_request(
        action_family=evidence_packet.action_family,
        environment=environment,
        workflow_pack_id=workflow_pack_id_for_action(evidence_packet.action_family),
        workflow_pack_version=workflow_pack_version_for_action(evidence_packet.action_family),
        approved_instruction_set=APPROVED_INSTRUCTION_SET,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        evaluation_pack_ref=EVALUATION_PACK_REF,
    )
    if not approval_decision.approved or approval_decision.approval is None:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason=approval_decision.code,
            caused_by=None,
            model_environment=environment,
        )

    try:
        response_status, payload = _execute_workflow_pack(
            evidence_packet=evidence_packet,
            audience=audience,
            requested_outputs=requested_outputs,
            requested_by=requested_by,
            reason=reason,
            model_approval=approval_decision.approval,
        )
    except (httpx.HTTPError, ValueError, LotusAIAdvisoryCopilotUnavailableError) as exc:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason="LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
            caused_by=exc,
            model_approval=approval_decision.approval,
            model_environment=environment,
        )

    return _draft_from_workflow_response(
        evidence_packet=evidence_packet,
        response_status=response_status,
        payload=payload,
        model_approval=approval_decision.approval,
        model_environment=environment,
    )


def _preflight_guardrail_rejection(
    *,
    evidence_packet: CopilotEvidencePacket,
    requested_intents: tuple[str, ...],
    user_instruction: str,
) -> AdvisoryCopilotAiDraft | None:
    preflight_reasons = evaluate_copilot_guardrails(
        requested_intents=requested_intents,
        source_refs_present=has_source_refs(evidence_packet),
        user_instruction=user_instruction,
        output_text="",
    )
    if not preflight_reasons:
        return None
    return _guardrail_rejected_draft(
        evidence_packet=evidence_packet,
        guardrail_reasons=preflight_reasons,
        fallback_reason="COPILOT_GUARDRAIL_PREFLIGHT_REJECTED",
    )


def _execute_workflow_pack(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: list[str],
    requested_by: str,
    reason: dict[str, Any],
    model_approval: AdvisoryCopilotModelApproval,
) -> tuple[int, dict[str, Any]]:
    base_url = _resolve_base_url()
    request_payload = _build_workflow_pack_request(
        evidence_packet=evidence_packet,
        audience=audience,
        requested_outputs=requested_outputs,
        requested_by=requested_by,
        reason=reason,
        model_approval=model_approval,
    )
    with httpx.Client(timeout=_resolve_timeout()) as client:
        response = client.post(
            f"{base_url}/platform/workflow-packs/execute",
            json=request_payload,
        )
        return response.status_code, response.json()


def _draft_from_workflow_response(
    *,
    evidence_packet: CopilotEvidencePacket,
    response_status: int,
    payload: dict[str, Any],
    model_approval: AdvisoryCopilotModelApproval,
    model_environment: str,
) -> AdvisoryCopilotAiDraft:
    if response_status != 200:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason=extract_error_detail(
                payload,
                default="LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
                max_length=MAX_COPILOT_LINEAGE_REF_LENGTH,
            ),
            caused_by=None,
            model_approval=model_approval,
            model_environment=model_environment,
        )

    execution = safe_dict(payload.get("execution"))
    if execution.get("status") != "COMPLETED":
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason="LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
            caused_by=None,
            model_approval=model_approval,
            model_environment=model_environment,
        )

    result = safe_dict(execution.get("result"))
    provider_id = extract_provider_id(result, max_length=MAX_COPILOT_LINEAGE_REF_LENGTH)
    model_version = extract_model_version(result, max_length=MAX_COPILOT_LINEAGE_REF_LENGTH)
    response_model_decision = validate_advisory_copilot_model_response(
        expected_approval=model_approval,
        provider_id=provider_id,
        model_version=model_version,
    )
    if not response_model_decision.approved:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason=response_model_decision.code,
            caused_by=None,
            model_approval=model_approval,
            model_environment=model_environment,
            provider_id=provider_id,
            model_version=model_version,
        )

    structured_output = safe_dict(result.get("structured_output"))
    raw_sections = structured_output.get("sections")
    sections = _map_sections(raw_sections)
    if not sections:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason="LOTUS_AI_ADVISORY_COPILOT_INVALID_OUTPUT",
            caused_by=None,
            model_approval=model_approval,
            model_environment=model_environment,
            provider_id=provider_id,
            model_version=model_version,
        )
    return _draft_from_completed_workflow_output(
        evidence_packet=evidence_packet,
        payload=payload,
        result=result,
        structured_output=structured_output,
        raw_sections=raw_sections,
        sections=sections,
        model_approval=model_approval,
        model_environment=model_environment,
        provider_id=provider_id,
        model_version=model_version,
    )


def _draft_from_completed_workflow_output(
    *,
    evidence_packet: CopilotEvidencePacket,
    payload: dict[str, Any],
    result: dict[str, Any],
    structured_output: dict[str, Any],
    raw_sections: Any,
    sections: tuple[dict[str, Any], ...],
    model_approval: AdvisoryCopilotModelApproval,
    model_environment: str,
    provider_id: str | None,
    model_version: str | None,
) -> AdvisoryCopilotAiDraft:
    output_reasons = evaluate_copilot_guardrails(
        requested_intents=(),
        source_refs_present=True,
        user_instruction="",
        output_text=" ".join(str(section.get("text", "")) for section in sections),
    )
    if output_reasons:
        return _guardrail_rejected_draft(
            evidence_packet=evidence_packet,
            guardrail_reasons=output_reasons,
            fallback_reason="COPILOT_OUTPUT_GUARDRAIL_REJECTED",
            workflow_run_id=extract_workflow_run_id(
                payload,
                max_length=MAX_COPILOT_LINEAGE_REF_LENGTH,
            ),
            model_version=model_version,
            provider_id=provider_id,
            model_approval=model_approval,
            model_environment=model_environment,
        )

    grounded_sections, grounding_summary = align_copilot_output_claims_to_evidence(
        evidence_packet=evidence_packet,
        raw_sections=raw_sections,
        output_sections=sections,
    )
    evaluation_result = evaluate_advisory_copilot_model_risk(
        action_family=evidence_packet.action_family,
        workflow_pack_id=workflow_pack_id_for_action(evidence_packet.action_family),
        workflow_pack_version=workflow_pack_version_for_action(evidence_packet.action_family),
        provider_id=provider_id,
        model_version=model_version,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        evaluation_pack_ref=EVALUATION_PACK_REF,
        draft_status=str(structured_output.get("state") or "REVIEW_REQUIRED"),
        output_section_count=len(grounded_sections),
        grounding_summary=grounding_summary,
        guardrail_reasons=(),
    )
    draft_status = (
        str(structured_output.get("state") or "REVIEW_REQUIRED")
        if grounding_summary["ready_for_review"] and evaluation_result.approved
        else "UNSUPPORTED"
    )

    return AdvisoryCopilotAiDraft(
        status=draft_status,
        sections=grounded_sections,
        lineage=_build_lineage(
            evidence_packet=evidence_packet,
            workflow_run_id=extract_workflow_run_id(
                payload,
                max_length=MAX_COPILOT_LINEAGE_REF_LENGTH,
            ),
            model_version=extract_model_version(
                result,
                max_length=MAX_COPILOT_LINEAGE_REF_LENGTH,
            ),
            provider_id=provider_id,
            model_approval=model_approval,
            model_environment=model_environment,
            fallback_reason=None,
            claim_grounding_summary=grounding_summary,
            model_risk_evaluation=evaluation_result,
        ),
        review_guidance=_map_string_list(structured_output.get("review_guidance")),
        guardrail_reasons=(),
    )


class LotusAIAdvisoryCopilotUnavailableError(Exception):
    pass


def build_advisory_copilot_unavailable_draft(
    *,
    evidence_packet: CopilotEvidencePacket,
    fallback_reason: str,
    caused_by: Exception | None = None,
    model_approval: AdvisoryCopilotModelApproval | None = None,
    model_environment: str | None = None,
    provider_id: str | None = None,
    model_version: str | None = None,
) -> AdvisoryCopilotAiDraft:
    if caused_by is not None:
        fallback_reason = fallback_reason or caused_by.__class__.__name__
    return AdvisoryCopilotAiDraft(
        status="UNAVAILABLE",
        sections=(),
        lineage=_build_lineage(
            evidence_packet=evidence_packet,
            workflow_run_id=None,
            model_version=model_version,
            provider_id=provider_id,
            fallback_reason=fallback_reason,
            model_approval=model_approval,
            model_environment=model_environment,
        ),
        review_guidance=(
            "Advisory copilot support is unavailable; use source evidence and deterministic "
            "advisory workflow sections only.",
            "Do not infer missing suitability, approval, policy, order, or client-ready "
            "communication evidence.",
        ),
        guardrail_reasons=(),
    )


def _guardrail_rejected_draft(
    *,
    evidence_packet: CopilotEvidencePacket,
    guardrail_reasons: tuple[CopilotGuardrailReasonCode, ...],
    fallback_reason: str,
    workflow_run_id: str | None = None,
    model_version: str | None = None,
    provider_id: str | None = None,
    model_approval: AdvisoryCopilotModelApproval | None = None,
    model_environment: str | None = None,
) -> AdvisoryCopilotAiDraft:
    return AdvisoryCopilotAiDraft(
        status="GUARDRAIL_REJECTED",
        sections=(),
        lineage=_build_lineage(
            evidence_packet=evidence_packet,
            workflow_run_id=workflow_run_id,
            model_version=model_version,
            provider_id=provider_id,
            fallback_reason=fallback_reason,
            model_approval=model_approval,
            model_environment=model_environment,
        ),
        review_guidance=(
            "The advisory copilot request was blocked by governed safety controls.",
            "Use source evidence and advisor workflow controls; do not bypass review or "
            "client-ready gates.",
        ),
        guardrail_reasons=guardrail_reasons,
    )


def _build_workflow_pack_request(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: list[str],
    requested_by: str,
    reason: dict[str, Any],
    model_approval: AdvisoryCopilotModelApproval,
) -> dict[str, object]:
    return cast(
        dict[str, object],
        build_advisory_copilot_workflow_pack_request(
            evidence_packet=evidence_packet,
            audience=audience,
            requested_outputs=requested_outputs,
            requested_by=requested_by,
            reason=reason,
            adapter_version=ADAPTER_VERSION,
            approved_instruction_set=APPROVED_INSTRUCTION_SET,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            output_schema_version=OUTPUT_SCHEMA_VERSION,
            evaluation_pack_ref=EVALUATION_PACK_REF,
            approved_provider_id=model_approval.provider_id,
            approved_model_version=model_approval.model_version,
            approval_reference=model_approval.approval_reference,
            change_reference=model_approval.change_reference,
            release_evidence_ref=model_approval.release_evidence_ref,
        ),
    )


def _resolve_base_url() -> str:
    return cast(
        str,
        resolve_lotus_ai_base_url(
            unavailable_error_type=LotusAIAdvisoryCopilotUnavailableError,
            unavailable_message="LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
        ),
    )


def _resolve_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_AI_TIMEOUT_SECONDS", default=10.0))


def _map_sections(value: Any) -> tuple[dict[str, Any], ...]:
    return cast(
        tuple[dict[str, Any], ...],
        map_review_required_sections(
            value,
            max_sections=MAX_COPILOT_OUTPUT_SECTIONS,
            max_section_key_length=MAX_COPILOT_SECTION_KEY_LENGTH,
            max_title_length=MAX_COPILOT_SECTION_TITLE_LENGTH,
            max_text_length=MAX_COPILOT_SECTION_TEXT_LENGTH,
        ),
    )


def _map_string_list(value: Any) -> tuple[str, ...]:
    return cast(
        tuple[str, ...],
        map_bounded_string_list(
            value,
            max_items=MAX_COPILOT_REVIEW_GUIDANCE_ITEMS,
            max_item_length=MAX_COPILOT_REVIEW_GUIDANCE_LENGTH,
        ),
    )


def _build_lineage(
    *,
    evidence_packet: CopilotEvidencePacket,
    workflow_run_id: str | None,
    model_version: str | None,
    provider_id: str | None = None,
    fallback_reason: str | None,
    model_approval: AdvisoryCopilotModelApproval | None = None,
    model_environment: str | None = None,
    claim_grounding_summary: dict[str, Any] | None = None,
    model_risk_evaluation: AdvisoryCopilotEvaluationResult | None = None,
) -> dict[str, Any]:
    lineage: dict[str, Any] = {
        "adapter_version": ADAPTER_VERSION,
        "workflow_pack_id": workflow_pack_id_for_action(evidence_packet.action_family),
        "workflow_pack_version": workflow_pack_version_for_action(evidence_packet.action_family),
        "workflow_surface": workflow_surface(evidence_packet.action_family),
        "workflow_run_id": workflow_run_id,
        "model_version": model_version,
        "model_provider_id": provider_id,
        "approved_instruction_set": APPROVED_INSTRUCTION_SET,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "evaluation_pack_ref": EVALUATION_PACK_REF,
        "evidence_packet_hash": evidence_packet.evidence_packet_hash,
        "proposal_version_id": _proposal_version_id(evidence_packet),
        "proposal_version_no": _proposal_version_no(evidence_packet),
        "fallback_reason": fallback_reason,
    }
    if model_approval is not None:
        lineage.update(model_approval.lineage(environment=model_environment or "DEVELOPMENT"))
    if claim_grounding_summary is not None:
        lineage["claim_grounding_summary"] = claim_grounding_summary
    if model_risk_evaluation is not None:
        lineage["model_risk_evaluation"] = model_risk_evaluation.lineage()
    return lineage


def _proposal_version_id(evidence_packet: CopilotEvidencePacket) -> str | None:
    return _proposal_version_lineage_id(evidence_packet) or _proposal_version_source_id(
        evidence_packet
    )


def _proposal_version_lineage_id(evidence_packet: CopilotEvidencePacket) -> str | None:
    for lineage_ref in evidence_packet.lineage_refs:
        if _is_proposal_version_lineage_ref(lineage_ref):
            return cast(str, lineage_ref.lineage_id)
    return None


def _is_proposal_version_lineage_ref(lineage_ref: CopilotLineageRef) -> bool:
    return (
        lineage_ref.source_system == "lotus-advise"
        and lineage_ref.lineage_type == "PROPOSAL_VERSION"
        and _is_present_string(lineage_ref.lineage_id)
    )


def _proposal_version_source_id(evidence_packet: CopilotEvidencePacket) -> str | None:
    for section in evidence_packet.sections:
        for source_ref in section.source_refs:
            if _is_proposal_version_source_ref(source_ref):
                return cast(str, source_ref.source_id)
    return None


def _is_proposal_version_source_ref(source_ref: CopilotSourceRef) -> bool:
    return (
        source_ref.source_system == "lotus-advise"
        and source_ref.source_type == "PROPOSAL_VERSION"
        and _is_present_string(source_ref.source_id)
    )


def _is_present_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _proposal_version_no(evidence_packet: CopilotEvidencePacket) -> int | None:
    for lineage_ref in evidence_packet.lineage_refs:
        if (
            lineage_ref.source_system == "lotus-advise"
            and lineage_ref.lineage_type == "PROPOSAL_VERSION_NO"
            and lineage_ref.lineage_id.isdigit()
        ):
            return int(lineage_ref.lineage_id)
    return None
