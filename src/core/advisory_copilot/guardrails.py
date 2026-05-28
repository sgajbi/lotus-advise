from __future__ import annotations

from types import MappingProxyType
from typing import Literal

CopilotGuardrailReasonCode = Literal[
    "AUTONOMOUS_ADVICE_FORBIDDEN",
    "TRADE_OR_ORDER_ACTION_FORBIDDEN",
    "POLICY_APPROVAL_FORBIDDEN",
    "CLIENT_READY_PUBLICATION_FORBIDDEN",
    "SOURCE_EVIDENCE_REQUIRED",
    "PROMPT_INJECTION_REJECTED",
    "SENSITIVE_DATA_EXPOSURE_REJECTED",
]

_FORBIDDEN_INTENT_REASON_CODES: dict[str, CopilotGuardrailReasonCode] = {
    "choose_recommendation": "AUTONOMOUS_ADVICE_FORBIDDEN",
    "rank_recommendations": "AUTONOMOUS_ADVICE_FORBIDDEN",
    "generate_trade": "TRADE_OR_ORDER_ACTION_FORBIDDEN",
    "create_order": "TRADE_OR_ORDER_ACTION_FORBIDDEN",
    "approve_policy": "POLICY_APPROVAL_FORBIDDEN",
    "waive_policy": "POLICY_APPROVAL_FORBIDDEN",
    "publish_client_ready": "CLIENT_READY_PUBLICATION_FORBIDDEN",
    "send_client_message": "CLIENT_READY_PUBLICATION_FORBIDDEN",
    "ignore_source_evidence": "SOURCE_EVIDENCE_REQUIRED",
    "override_instructions": "PROMPT_INJECTION_REJECTED",
    "expose_raw_payload": "SENSITIVE_DATA_EXPOSURE_REJECTED",
}

FORBIDDEN_INTENT_REASON_CODES = MappingProxyType(_FORBIDDEN_INTENT_REASON_CODES)

_PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore the above",
    "system prompt",
    "developer message",
    "override instructions",
    "bypass guardrail",
)

_CLIENT_READY_MARKERS = (
    "approved for client",
    "client-ready publication approved",
    "client-ready publication is approved",
    "client-ready publication enabled",
    "client-ready publication is enabled",
    "client-ready publication permitted",
    "client-ready publication is permitted",
    "ready to send to client",
    "send this to the client",
    "final client advice",
)

_SENSITIVE_OUTPUT_MARKERS = (
    "raw prompt",
    "provider response",
    "trace id",
    "correlation id",
    "raw payload",
)


def guardrail_reason_for_intent(intent_key: str) -> CopilotGuardrailReasonCode | None:
    normalized = intent_key.strip().lower().replace("-", "_").replace(" ", "_")
    return FORBIDDEN_INTENT_REASON_CODES.get(normalized)


def evaluate_copilot_guardrails(
    *,
    requested_intents: tuple[str, ...],
    source_refs_present: bool,
    user_instruction: str,
    output_text: str,
) -> tuple[CopilotGuardrailReasonCode, ...]:
    reasons: list[CopilotGuardrailReasonCode] = []

    for intent in requested_intents:
        reason = guardrail_reason_for_intent(intent)
        if reason is not None:
            reasons.append(reason)

    if not source_refs_present:
        reasons.append("SOURCE_EVIDENCE_REQUIRED")

    instruction = user_instruction.lower()
    if any(marker in instruction for marker in _PROMPT_INJECTION_MARKERS):
        reasons.append("PROMPT_INJECTION_REJECTED")

    output = output_text.lower()
    if any(marker in output for marker in _CLIENT_READY_MARKERS):
        reasons.append("CLIENT_READY_PUBLICATION_FORBIDDEN")
    if any(marker in output for marker in _SENSITIVE_OUTPUT_MARKERS):
        reasons.append("SENSITIVE_DATA_EXPOSURE_REJECTED")

    return tuple(dict.fromkeys(reasons))
