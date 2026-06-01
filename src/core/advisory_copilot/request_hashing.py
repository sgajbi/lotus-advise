from __future__ import annotations

import hashlib
import json
from typing import Any

from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.structured_payload import assert_safe_structured_payload
from src.core.advisory_copilot.type_models import CopilotAudience


def build_advisory_copilot_run_request_hash(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: tuple[str, ...],
    requested_by: str,
    reason: dict[str, Any],
    requested_intents: tuple[str, ...],
    user_instruction: str,
) -> str:
    return canonical_json_hash(
        build_advisory_copilot_run_request_summary(
            evidence_packet=evidence_packet,
            audience=audience,
            requested_outputs=requested_outputs,
            requested_by=requested_by,
            reason=reason,
            requested_intents=requested_intents,
            user_instruction=user_instruction,
        )
    )


def build_advisory_copilot_run_request_summary(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: tuple[str, ...],
    requested_by: str,
    reason: dict[str, Any],
    requested_intents: tuple[str, ...],
    user_instruction: str,
) -> dict[str, Any]:
    assert_safe_structured_payload(reason)
    return {
        "action_family": evidence_packet.action_family,
        "audience": audience,
        "portfolio_id": evidence_packet.portfolio_id,
        "proposal_id": evidence_packet.proposal_id,
        "evidence_packet_id": evidence_packet.evidence_packet_id,
        "evidence_packet_hash": evidence_packet.evidence_packet_hash,
        "requested_outputs": list(requested_outputs),
        "requested_by": requested_by,
        "reason": reason,
        "requested_intents": list(requested_intents),
        "user_instruction_hash": optional_user_instruction_hash(user_instruction),
    }


def canonical_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def optional_user_instruction_hash(value: str) -> str | None:
    stripped = value.strip()
    if not stripped:
        return None
    return canonical_json_hash({"user_instruction": stripped})
