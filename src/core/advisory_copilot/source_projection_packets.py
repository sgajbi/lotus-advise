from __future__ import annotations

from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord

SOURCE_PROJECTION_PROPOSAL_VERSION = "PROPOSAL_VERSION"


def can_refresh_source_projection_packet(
    *,
    existing: AdvisoryCopilotEvidencePacketRecord,
    incoming: AdvisoryCopilotEvidencePacketRecord,
) -> bool:
    return bool(
        _same_proposal_version_projection(existing=existing, incoming=incoming)
        and _same_proposal_version_source(existing=existing, incoming=incoming)
        and _same_packet_identity(existing=existing, incoming=incoming)
    )


def _same_proposal_version_projection(
    *,
    existing: AdvisoryCopilotEvidencePacketRecord,
    incoming: AdvisoryCopilotEvidencePacketRecord,
) -> bool:
    return bool(
        existing.reason_json.get("source_projection") == SOURCE_PROJECTION_PROPOSAL_VERSION
        and incoming.reason_json.get("source_projection") == SOURCE_PROJECTION_PROPOSAL_VERSION
    )


def _same_proposal_version_source(
    *,
    existing: AdvisoryCopilotEvidencePacketRecord,
    incoming: AdvisoryCopilotEvidencePacketRecord,
) -> bool:
    return bool(
        existing.reason_json.get("proposal_id") == incoming.reason_json.get("proposal_id")
        and existing.reason_json.get("proposal_version_no")
        == incoming.reason_json.get("proposal_version_no")
    )


def _same_packet_identity(
    *,
    existing: AdvisoryCopilotEvidencePacketRecord,
    incoming: AdvisoryCopilotEvidencePacketRecord,
) -> bool:
    return bool(
        existing.action_family == incoming.action_family
        and existing.audience == incoming.audience
        and existing.portfolio_id == incoming.portfolio_id
        and existing.proposal_id == incoming.proposal_id
    )
