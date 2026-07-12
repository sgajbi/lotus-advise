from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
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

_BASE64_CANDIDATE_PATTERN = re.compile(r"\b[A-Za-z0-9+/=_-]{12,}\b")
_WORD_SEPARATOR_PATTERN = re.compile(r"[^a-z0-9]+")
_PRINTABLE_ASCII_PATTERN = re.compile(r"^[\x09\x0a\x0d\x20-\x7e]+$")

_PROMPT_INJECTION_PHRASES = (
    "disregard previous instructions",
    "disregard prior directions",
    "ignore previous instructions",
    "ignore the above",
    "ignore prior instructions",
    "ignore all earlier instructions",
    "system prompt",
    "developer message",
    "override instructions",
    "override safety instructions",
    "bypass guardrail",
    "bypass the guardrail",
    "jailbreak",
    "act as system",
)

_AUTONOMOUS_ADVICE_PHRASES = (
    "choose recommendation",
    "choose the recommendation",
    "rank recommendations",
    "select the best recommendation",
    "decide the best option",
    "make the investment decision",
)

_TRADE_OR_ORDER_PHRASES = (
    "generate trade",
    "create order",
    "place trade",
    "place the trade",
    "execute order",
    "execute the order",
    "submit order",
    "book trade",
)

_POLICY_APPROVAL_PHRASES = (
    "approve policy",
    "approve the policy",
    "waive policy",
    "waive the policy",
    "policy waiver approved",
    "policy is approved",
    "override compliance",
)

_CLIENT_READY_PHRASES = (
    "approved for client",
    "client-ready publication approved",
    "client-ready publication is approved",
    "client-ready publication enabled",
    "client-ready publication is enabled",
    "client-ready publication permitted",
    "client-ready publication is permitted",
    "ready to send to client",
    "ready to send to the client",
    "send this to the client",
    "final client advice",
)

_SENSITIVE_OUTPUT_PHRASES = (
    "raw prompt",
    "provider response",
    "trace id",
    "correlation id",
    "raw payload",
    "api key",
    "bearer token",
)

_TEXT_RULES: tuple[tuple[CopilotGuardrailReasonCode, tuple[str, ...]], ...] = (
    ("AUTONOMOUS_ADVICE_FORBIDDEN", _AUTONOMOUS_ADVICE_PHRASES),
    ("TRADE_OR_ORDER_ACTION_FORBIDDEN", _TRADE_OR_ORDER_PHRASES),
    ("POLICY_APPROVAL_FORBIDDEN", _POLICY_APPROVAL_PHRASES),
    ("CLIENT_READY_PUBLICATION_FORBIDDEN", _CLIENT_READY_PHRASES),
    ("SENSITIVE_DATA_EXPOSURE_REJECTED", _SENSITIVE_OUTPUT_PHRASES),
)


@dataclass(frozen=True)
class CopilotGuardrailSourceEvidence:
    section_key: str
    title: str
    summary_items: tuple[str, ...]
    source_ref_count: int


@dataclass(frozen=True)
class CopilotGuardrailPolicyInput:
    requested_intents: tuple[str, ...] = ()
    source_evidence: tuple[CopilotGuardrailSourceEvidence, ...] = ()
    user_instruction: str = ""
    model_output_sections: tuple[str, ...] = ()


def guardrail_reason_for_intent(intent_key: str) -> CopilotGuardrailReasonCode | None:
    normalized = intent_key.strip().lower().replace("-", "_").replace(" ", "_")
    return FORBIDDEN_INTENT_REASON_CODES.get(normalized)


def evaluate_copilot_guardrail_policy(
    policy_input: CopilotGuardrailPolicyInput,
) -> tuple[CopilotGuardrailReasonCode, ...]:
    reasons: list[CopilotGuardrailReasonCode] = []
    reasons.extend(_intent_guardrail_reasons(policy_input.requested_intents))
    reasons.extend(_source_evidence_guardrail_reasons(policy_input.source_evidence))
    reasons.extend(_text_guardrail_reasons(policy_input.user_instruction, include_sensitive=False))
    reasons.extend(_source_text_guardrail_reasons(policy_input.source_evidence))
    reasons.extend(
        _text_guardrail_reasons(
            " ".join(policy_input.model_output_sections),
            include_sensitive=True,
        )
    )

    return tuple(dict.fromkeys(reasons))


def evaluate_copilot_guardrails(
    *,
    requested_intents: tuple[str, ...],
    source_refs_present: bool,
    user_instruction: str,
    output_text: str,
) -> tuple[CopilotGuardrailReasonCode, ...]:
    return evaluate_copilot_guardrail_policy(
        CopilotGuardrailPolicyInput(
            requested_intents=requested_intents,
            source_evidence=(
                CopilotGuardrailSourceEvidence(
                    section_key="LEGACY_SOURCE_REF_CHECK",
                    title="Legacy source reference check",
                    summary_items=(),
                    source_ref_count=1 if source_refs_present else 0,
                ),
            ),
            user_instruction=user_instruction,
            model_output_sections=(output_text,),
        )
    )


def _intent_guardrail_reasons(
    requested_intents: tuple[str, ...],
) -> tuple[CopilotGuardrailReasonCode, ...]:
    reasons: list[CopilotGuardrailReasonCode] = []
    for intent in requested_intents:
        reason = guardrail_reason_for_intent(intent)
        if reason is not None:
            reasons.append(reason)
    return tuple(reasons)


def _source_evidence_guardrail_reasons(
    source_evidence: tuple[CopilotGuardrailSourceEvidence, ...],
) -> tuple[CopilotGuardrailReasonCode, ...]:
    if any(item.source_ref_count > 0 for item in source_evidence):
        return ()
    return ("SOURCE_EVIDENCE_REQUIRED",)


def _source_text_guardrail_reasons(
    source_evidence: tuple[CopilotGuardrailSourceEvidence, ...],
) -> tuple[CopilotGuardrailReasonCode, ...]:
    source_text = " ".join(
        fragment
        for item in source_evidence
        for fragment in (item.title, *item.summary_items)
        if fragment
    )
    if _contains_phrase(source_text, _PROMPT_INJECTION_PHRASES):
        return ("PROMPT_INJECTION_REJECTED",)
    return ()


def _text_guardrail_reasons(
    text: str,
    *,
    include_sensitive: bool,
) -> tuple[CopilotGuardrailReasonCode, ...]:
    reasons: list[CopilotGuardrailReasonCode] = []
    if _contains_phrase(text, _PROMPT_INJECTION_PHRASES):
        reasons.append("PROMPT_INJECTION_REJECTED")
    for reason, phrases in _TEXT_RULES:
        if reason == "SENSITIVE_DATA_EXPOSURE_REJECTED" and not include_sensitive:
            continue
        if _contains_phrase(text, phrases):
            reasons.append(reason)
    return tuple(reasons)


def _contains_phrase(value: str, phrases: tuple[str, ...]) -> bool:
    if not value:
        return False
    normalized_values = _normalized_text_variants(value)
    return any(_phrase_matches(phrase, normalized_values) for phrase in phrases)


def _phrase_matches(phrase: str, normalized_values: tuple[str, ...]) -> bool:
    normalized_phrase = _normalize_for_phrase_match(phrase)
    compact_phrase = _compact_for_phrase_match(phrase)
    return any(
        normalized_phrase in normalized_value or compact_phrase in normalized_value
        for normalized_value in normalized_values
    )


def _normalized_text_variants(value: str) -> tuple[str, ...]:
    variants = [_normalize_for_phrase_match(value), _compact_for_phrase_match(value)]
    for decoded in _decoded_base64_candidates(value):
        variants.append(_normalize_for_phrase_match(decoded))
        variants.append(_compact_for_phrase_match(decoded))
    return tuple(dict.fromkeys(item for item in variants if item))


def _normalize_for_phrase_match(value: str) -> str:
    lowered = value.lower()
    return _WORD_SEPARATOR_PATTERN.sub(" ", lowered).strip()


def _compact_for_phrase_match(value: str) -> str:
    return _WORD_SEPARATOR_PATTERN.sub("", value.lower())


def _decoded_base64_candidates(value: str) -> tuple[str, ...]:
    decoded_values: list[str] = []
    for candidate in _BASE64_CANDIDATE_PATTERN.findall(value):
        decoded = _decode_base64_candidate(candidate)
        if decoded:
            decoded_values.append(decoded)
    return tuple(decoded_values)


def _decode_base64_candidate(candidate: str) -> str | None:
    normalized = candidate.replace("-", "+").replace("_", "/")
    padded = normalized + ("=" * ((4 - len(normalized) % 4) % 4))
    try:
        decoded = base64.b64decode(padded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    if not _PRINTABLE_ASCII_PATTERN.match(decoded):
        return None
    return decoded
