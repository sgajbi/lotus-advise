from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, cast

import httpx

from src.core.advisory_copilot import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotEvidencePacket,
    CopilotGuardrailReasonCode,
    evaluate_copilot_guardrails,
    workflow_pack_id_for_action,
    workflow_pack_version_for_action,
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
from src.integrations.lotus_ai.runtime_config import (
    resolve_lotus_ai_base_url,
    resolve_lotus_ai_tenant_id,
)
from src.integrations.lotus_core.runtime_config import env_positive_float

ADAPTER_VERSION = "advisory-copilot-lotus-ai-adapter.v1"
APPROVED_INSTRUCTION_SET = "advisory-copilot-instructions.v1"
PROMPT_TEMPLATE_VERSION = "advisory-copilot-prompt-template.v1"
OUTPUT_SCHEMA_VERSION = "advisory-copilot-output-schema.v1"
EVALUATION_PACK_REF = "advisory-copilot-eval-pack.v1"
WORKFLOW_SURFACE_PREFIX = "advisory-copilot"
MAX_COPILOT_OUTPUT_SECTIONS = DEFAULT_AI_OUTPUT_SECTION_LIMIT
MAX_COPILOT_SECTION_KEY_LENGTH = DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH
MAX_COPILOT_SECTION_TITLE_LENGTH = DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH
MAX_COPILOT_SECTION_TEXT_LENGTH = DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH
MAX_COPILOT_REVIEW_GUIDANCE_ITEMS = DEFAULT_AI_REVIEW_GUIDANCE_LIMIT
MAX_COPILOT_REVIEW_GUIDANCE_LENGTH = DEFAULT_AI_REVIEW_GUIDANCE_LENGTH
MAX_COPILOT_CALLER_CORRELATION_ID_LENGTH = 128
MAX_COPILOT_REQUESTED_OUTPUTS = 8
MAX_COPILOT_REQUESTED_OUTPUT_LENGTH = 96
MAX_COPILOT_REQUESTED_BY_LENGTH = 128
MAX_COPILOT_REASON_KEYS = 16
MAX_COPILOT_REASON_KEY_LENGTH = 64
MAX_COPILOT_REASON_TEXT_LENGTH = 1000
MAX_COPILOT_REASON_LIST_ITEMS = 8
MAX_COPILOT_SOURCE_REFS = 32
MAX_COPILOT_SOURCE_REF_LENGTH = 512
MAX_COPILOT_LINEAGE_REF_LENGTH = 160
_RAW_REASON_KEYS = frozenset(
    {
        "prompt",
        "raw_prompt",
        "raw_output",
        "unsafe_output",
        "provider_response",
        "model_response",
        "instruction",
        "system_instruction",
    }
)


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
    preflight_reasons = evaluate_copilot_guardrails(
        requested_intents=requested_intents,
        source_refs_present=_has_source_refs(evidence_packet),
        user_instruction=user_instruction,
        output_text="",
    )
    if preflight_reasons:
        return _guardrail_rejected_draft(
            evidence_packet=evidence_packet,
            guardrail_reasons=preflight_reasons,
            fallback_reason="COPILOT_GUARDRAIL_PREFLIGHT_REJECTED",
        )

    try:
        base_url = _resolve_base_url()
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}/platform/workflow-packs/execute",
                json=_build_workflow_pack_request(
                    evidence_packet=evidence_packet,
                    audience=audience,
                    requested_outputs=requested_outputs,
                    requested_by=requested_by,
                    reason=reason,
                ),
            )
            payload = response.json()
    except (httpx.HTTPError, ValueError, LotusAIAdvisoryCopilotUnavailableError) as exc:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason="LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
            caused_by=exc,
        )

    if response.status_code != 200:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason=_extract_detail(payload),
            caused_by=None,
        )

    execution = _safe_dict(payload.get("execution"))
    if execution.get("status") != "COMPLETED":
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason="LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
            caused_by=None,
        )

    result = _safe_dict(execution.get("result"))
    structured_output = _safe_dict(result.get("structured_output"))
    sections = _map_sections(structured_output.get("sections"))
    if not sections:
        return build_advisory_copilot_unavailable_draft(
            evidence_packet=evidence_packet,
            fallback_reason="LOTUS_AI_ADVISORY_COPILOT_INVALID_OUTPUT",
            caused_by=None,
        )
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
            workflow_run_id=_extract_workflow_run_id(payload),
            model_version=_extract_model_version(result),
        )

    return AdvisoryCopilotAiDraft(
        status=str(structured_output.get("state") or "REVIEW_REQUIRED"),
        sections=sections,
        lineage=_build_lineage(
            evidence_packet=evidence_packet,
            workflow_run_id=_extract_workflow_run_id(payload),
            model_version=_extract_model_version(result),
            fallback_reason=None,
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
) -> AdvisoryCopilotAiDraft:
    if caused_by is not None:
        fallback_reason = fallback_reason or caused_by.__class__.__name__
    return AdvisoryCopilotAiDraft(
        status="UNAVAILABLE",
        sections=(),
        lineage=_build_lineage(
            evidence_packet=evidence_packet,
            workflow_run_id=None,
            model_version=None,
            fallback_reason=fallback_reason,
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
) -> AdvisoryCopilotAiDraft:
    return AdvisoryCopilotAiDraft(
        status="GUARDRAIL_REJECTED",
        sections=(),
        lineage=_build_lineage(
            evidence_packet=evidence_packet,
            workflow_run_id=workflow_run_id,
            model_version=model_version,
            fallback_reason=fallback_reason,
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
) -> dict[str, object]:
    action_family = evidence_packet.action_family
    return {
        "pack_id": workflow_pack_id_for_action(action_family),
        "version": workflow_pack_version_for_action(action_family),
        "environment": os.getenv("LOTUS_AI_WORKFLOW_PACK_ENVIRONMENT", "DEVELOPMENT"),
        "caller_identity_class": "INTERNAL_SERVICE",
        "workflow_surface": _workflow_surface(action_family),
        "task_request": {
            "task_id": "explain.v1",
            "input_mode": "STRUCTURED_CONTEXT",
            "caller": {
                "caller_app": "lotus-advise",
                "correlation_id": _caller_correlation_id(evidence_packet),
                "requested_by": _bounded_text(
                    requested_by,
                    max_length=MAX_COPILOT_REQUESTED_BY_LENGTH,
                ),
                "tenant_id": resolve_lotus_ai_tenant_id(),
            },
            "context": {
                "summary": "Draft review-gated advisory copilot output from bounded evidence.",
                "payload": {
                    "copilot_evidence_packet": evidence_packet.model_dump(mode="json"),
                    "copilot_request": {
                        "action_family": action_family,
                        "audience": audience,
                        "requested_outputs": _requested_outputs(requested_outputs),
                        "requested_by": _bounded_text(
                            requested_by,
                            max_length=MAX_COPILOT_REQUESTED_BY_LENGTH,
                        ),
                        "reason": _safe_reason(reason),
                    },
                    "model_risk_controls": {
                        "adapter_version": ADAPTER_VERSION,
                        "approved_instruction_set": APPROVED_INSTRUCTION_SET,
                        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                        "output_schema_version": OUTPUT_SCHEMA_VERSION,
                        "evaluation_pack_ref": EVALUATION_PACK_REF,
                    },
                    "supportability": {
                        "human_review_required": True,
                        "client_ready_publication": "BLOCKED",
                        "unsupported_claims": [
                            "client_ready_publication",
                            "policy_approval",
                            "trade_or_order_action",
                            "missing_evidence_inference",
                        ],
                    },
                },
                "source_refs": _source_refs(evidence_packet),
            },
            "expected_output_label": "EXPLANATION_ONLY",
        },
    }


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


def _workflow_surface(action_family: CopilotActionFamily) -> str:
    return f"{WORKFLOW_SURFACE_PREFIX}-{action_family.lower().replace('_', '-')}"


def _source_refs(evidence_packet: CopilotEvidencePacket) -> list[str]:
    refs = [
        f"lotus-advise:copilot-evidence-packet:{evidence_packet.evidence_packet_id}",
        f"lotus-advise:copilot-evidence-packet-hash:{evidence_packet.evidence_packet_hash}",
    ]
    for section in evidence_packet.sections:
        for source_ref in section.source_refs:
            refs.append(
                ":".join(
                    (
                        source_ref.source_system,
                        source_ref.source_type,
                        source_ref.source_id,
                        source_ref.content_hash or "no-content-hash",
                    )
                )
            )
    return [_bounded_text(ref, max_length=MAX_COPILOT_SOURCE_REF_LENGTH) for ref in refs][
        :MAX_COPILOT_SOURCE_REFS
    ]


def _has_source_refs(evidence_packet: CopilotEvidencePacket) -> bool:
    return any(section.source_refs for section in evidence_packet.sections)


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
    fallback_reason: str | None,
) -> dict[str, Any]:
    return {
        "adapter_version": ADAPTER_VERSION,
        "workflow_pack_id": workflow_pack_id_for_action(evidence_packet.action_family),
        "workflow_pack_version": workflow_pack_version_for_action(evidence_packet.action_family),
        "workflow_surface": _workflow_surface(evidence_packet.action_family),
        "workflow_run_id": workflow_run_id,
        "model_version": model_version,
        "approved_instruction_set": APPROVED_INSTRUCTION_SET,
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "evaluation_pack_ref": EVALUATION_PACK_REF,
        "evidence_packet_hash": evidence_packet.evidence_packet_hash,
        "proposal_version_id": _proposal_version_id(evidence_packet),
        "proposal_version_no": _proposal_version_no(evidence_packet),
        "fallback_reason": fallback_reason,
    }


def _proposal_version_id(evidence_packet: CopilotEvidencePacket) -> str | None:
    for lineage_ref in evidence_packet.lineage_refs:
        lineage_id = lineage_ref.lineage_id
        if (
            lineage_ref.source_system == "lotus-advise"
            and lineage_ref.lineage_type == "PROPOSAL_VERSION"
            and isinstance(lineage_id, str)
            and lineage_id
        ):
            return lineage_id
    for section in evidence_packet.sections:
        for source_ref in section.source_refs:
            source_id = source_ref.source_id
            if (
                source_ref.source_system == "lotus-advise"
                and source_ref.source_type == "PROPOSAL_VERSION"
                and isinstance(source_id, str)
                and source_id
            ):
                return source_id
    return None


def _proposal_version_no(evidence_packet: CopilotEvidencePacket) -> int | None:
    for lineage_ref in evidence_packet.lineage_refs:
        if (
            lineage_ref.source_system == "lotus-advise"
            and lineage_ref.lineage_type == "PROPOSAL_VERSION_NO"
            and lineage_ref.lineage_id.isdigit()
        ):
            return int(lineage_ref.lineage_id)
    return None


def _extract_workflow_run_id(payload: dict[str, Any]) -> str | None:
    workflow_pack_run = _safe_dict(payload.get("workflow_pack_run"))
    return _optional_bounded_text(
        workflow_pack_run.get("run_id"),
        max_length=MAX_COPILOT_LINEAGE_REF_LENGTH,
    )


def _extract_model_version(result: dict[str, Any]) -> str | None:
    return _optional_bounded_text(
        result.get("model_version"),
        max_length=MAX_COPILOT_LINEAGE_REF_LENGTH,
    )


def _extract_detail(payload: dict[str, Any]) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return _bounded_text(detail, max_length=MAX_COPILOT_LINEAGE_REF_LENGTH)
    return "LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _caller_correlation_id(evidence_packet: CopilotEvidencePacket) -> str:
    candidate = f"advisory-copilot-{evidence_packet.evidence_packet_id}"
    if len(candidate) <= MAX_COPILOT_CALLER_CORRELATION_ID_LENGTH:
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
    return f"advisory-copilot-{digest}"


def _requested_outputs(values: list[str]) -> list[str]:
    bounded: list[str] = []
    seen: set[str] = set()
    for value in values:
        output = _bounded_text(value, max_length=MAX_COPILOT_REQUESTED_OUTPUT_LENGTH)
        if not output or output in seen:
            continue
        bounded.append(output)
        seen.add(output)
        if len(bounded) >= MAX_COPILOT_REQUESTED_OUTPUTS:
            break
    return bounded


def _safe_reason(reason: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in reason.items():
        key_text = _bounded_text(str(key), max_length=MAX_COPILOT_REASON_KEY_LENGTH)
        if not key_text or key_text.strip().lower() in _RAW_REASON_KEYS:
            continue
        safe_value = _safe_reason_value(value)
        if safe_value is not None:
            safe[key_text] = safe_value
        if len(safe) >= MAX_COPILOT_REASON_KEYS:
            break
    return safe


def _safe_reason_value(value: Any) -> str | int | bool | None | list[str]:
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, str):
        return _bounded_text(value, max_length=MAX_COPILOT_REASON_TEXT_LENGTH) or None
    if isinstance(value, list | tuple):
        items = [
            _bounded_text(item, max_length=MAX_COPILOT_REASON_TEXT_LENGTH)
            for item in value
            if isinstance(item, str)
        ]
        return [item for item in items if item][:MAX_COPILOT_REASON_LIST_ITEMS] or None
    return _bounded_text(str(value), max_length=MAX_COPILOT_REASON_TEXT_LENGTH) or None


def _optional_bounded_text(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    return _bounded_text(value, max_length=max_length) or None


def _bounded_text(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    suffix = "..."
    return normalized[: max_length - len(suffix)].rstrip() + suffix
