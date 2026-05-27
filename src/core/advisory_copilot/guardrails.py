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


def guardrail_reason_for_intent(intent_key: str) -> CopilotGuardrailReasonCode | None:
    normalized = intent_key.strip().lower().replace("-", "_").replace(" ", "_")
    return FORBIDDEN_INTENT_REASON_CODES.get(normalized)

