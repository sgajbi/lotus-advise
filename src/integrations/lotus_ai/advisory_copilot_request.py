from __future__ import annotations

import hashlib
from typing import Any, TypeGuard, cast

from src.core.advisory_copilot import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotEvidencePacket,
    workflow_pack_id_for_action,
    workflow_pack_version_for_action,
)
from src.integrations.lotus_ai.workflow_request import build_workflow_pack_execute_request

WORKFLOW_SURFACE_PREFIX = "advisory-copilot"
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
SafeReasonScalar = bool | int | None


def build_advisory_copilot_workflow_pack_request(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: list[str],
    requested_by: str,
    reason: dict[str, Any],
    adapter_version: str,
    approved_instruction_set: str,
    prompt_template_version: str,
    output_schema_version: str,
    evaluation_pack_ref: str,
) -> dict[str, object]:
    action_family = evidence_packet.action_family
    bounded_requested_by = bounded_text(
        requested_by,
        max_length=MAX_COPILOT_REQUESTED_BY_LENGTH,
    )
    return cast(
        dict[str, object],
        build_workflow_pack_execute_request(
            pack_id=workflow_pack_id_for_action(action_family),
            version=workflow_pack_version_for_action(action_family),
            workflow_surface=workflow_surface(action_family),
            task_id="explain.v1",
            correlation_id=caller_correlation_id(evidence_packet),
            requested_by=bounded_requested_by,
            context_summary="Draft review-gated advisory copilot output from bounded evidence.",
            context_payload={
                "copilot_evidence_packet": evidence_packet.model_dump(mode="json"),
                "copilot_request": {
                    "action_family": action_family,
                    "audience": audience,
                    "requested_outputs": requested_output_keys(requested_outputs),
                    "requested_by": bounded_requested_by,
                    "reason": safe_reason(reason),
                },
                "model_risk_controls": {
                    "adapter_version": adapter_version,
                    "approved_instruction_set": approved_instruction_set,
                    "prompt_template_version": prompt_template_version,
                    "output_schema_version": output_schema_version,
                    "evaluation_pack_ref": evaluation_pack_ref,
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
            source_refs=source_refs(evidence_packet),
            expected_output_label="EXPLANATION_ONLY",
        ),
    )


def workflow_surface(action_family: CopilotActionFamily) -> str:
    return f"{WORKFLOW_SURFACE_PREFIX}-{action_family.lower().replace('_', '-')}"


def source_refs(evidence_packet: CopilotEvidencePacket) -> list[str]:
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
    return [bounded_text(ref, max_length=MAX_COPILOT_SOURCE_REF_LENGTH) for ref in refs][
        :MAX_COPILOT_SOURCE_REFS
    ]


def has_source_refs(evidence_packet: CopilotEvidencePacket) -> bool:
    return any(section.source_refs for section in evidence_packet.sections)


def caller_correlation_id(evidence_packet: CopilotEvidencePacket) -> str:
    candidate = f"advisory-copilot-{evidence_packet.evidence_packet_id}"
    if len(candidate) <= MAX_COPILOT_CALLER_CORRELATION_ID_LENGTH:
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
    return f"advisory-copilot-{digest}"


def requested_output_keys(values: list[str]) -> list[str]:
    bounded: list[str] = []
    seen: set[str] = set()
    for value in values:
        output = bounded_text(value, max_length=MAX_COPILOT_REQUESTED_OUTPUT_LENGTH)
        if not output or output in seen:
            continue
        bounded.append(output)
        seen.add(output)
        if len(bounded) >= MAX_COPILOT_REQUESTED_OUTPUTS:
            break
    return bounded


def safe_reason(reason: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in reason.items():
        key_text = bounded_text(str(key), max_length=MAX_COPILOT_REASON_KEY_LENGTH)
        if not key_text or key_text.strip().lower() in _RAW_REASON_KEYS:
            continue
        safe_value = _safe_reason_value(value)
        if safe_value is not None:
            safe[key_text] = safe_value
        if len(safe) >= MAX_COPILOT_REASON_KEYS:
            break
    return safe


def _safe_reason_value(value: Any) -> str | int | bool | None | list[str]:
    if is_safe_scalar_reason_value(value):
        return value
    if isinstance(value, str):
        return safe_reason_text(value)
    if isinstance(value, list | tuple):
        return safe_reason_list(value)
    return safe_reason_text(str(value))


def is_safe_scalar_reason_value(value: Any) -> TypeGuard[SafeReasonScalar]:
    return value is None or isinstance(value, bool | int)


def safe_reason_text(value: str) -> str | None:
    return bounded_text(value, max_length=MAX_COPILOT_REASON_TEXT_LENGTH) or None


def safe_reason_list(value: list[Any] | tuple[Any, ...]) -> list[str] | None:
    items = [
        bounded
        for bounded in (safe_reason_text(item) for item in value if isinstance(item, str))
        if bounded
    ]
    return items[:MAX_COPILOT_REASON_LIST_ITEMS] or None


def bounded_text(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    suffix = "..."
    return normalized[: max_length - len(suffix)].rstrip() + suffix
