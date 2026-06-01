from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.structured_payload import assert_safe_structured_payload
from src.core.advisory_copilot.type_models import CopilotAudience


def save_advisory_copilot_evidence_packet(
    *,
    repository: AdvisoryCopilotRepository,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    created_by: str,
    reason: dict[str, Any],
    correlation_id: str,
    created_at: datetime | None = None,
) -> AdvisoryCopilotEvidencePacketRecord:
    assert_safe_structured_payload(reason)
    record = AdvisoryCopilotEvidencePacketRecord(
        evidence_packet_id=evidence_packet.evidence_packet_id,
        evidence_packet_hash=evidence_packet.evidence_packet_hash,
        action_family=evidence_packet.action_family,
        audience=audience,
        portfolio_id=evidence_packet.portfolio_id,
        proposal_id=evidence_packet.proposal_id,
        created_by=created_by,
        created_at=created_at or datetime.now(timezone.utc),
        correlation_id=correlation_id,
        packet_json=evidence_packet.model_dump(mode="json"),
        reason_json=dict(reason),
    )
    return repository.save_evidence_packet(record)


def load_advisory_copilot_evidence_packet(
    *, repository: AdvisoryCopilotRepository, evidence_packet_id: str
) -> CopilotEvidencePacket:
    record = repository.get_evidence_packet(evidence_packet_id=evidence_packet_id)
    if record is None:
        raise ValueError("COPILOT_EVIDENCE_PACKET_NOT_FOUND")
    return cast(CopilotEvidencePacket, CopilotEvidencePacket.model_validate(record.packet_json))
