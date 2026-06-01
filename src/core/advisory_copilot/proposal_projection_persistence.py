from __future__ import annotations

from collections.abc import Sequence

from src.core.advisory_copilot.api_models import (
    AdvisoryCopilotEvidencePacketResponse,
    AdvisoryCopilotProposalVersionEvidenceRequest,
)
from src.core.advisory_copilot.correlation import resolve_advisory_copilot_correlation_id
from src.core.advisory_copilot.packet_persistence import save_advisory_copilot_evidence_packet
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.source_projection import (
    build_proposal_version_copilot_evidence_packet,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.repository import ProposalRepository


def save_proposal_version_advisory_copilot_evidence_packet(
    *,
    repository: AdvisoryCopilotRepository,
    proposal_repository: ProposalRepository,
    payload: AdvisoryCopilotProposalVersionEvidenceRequest,
    policy_evaluations: Sequence[PolicyEvaluationRecord],
    correlation_id: str | None,
) -> AdvisoryCopilotEvidencePacketResponse:
    packet = build_proposal_version_copilot_evidence_packet(
        repository=proposal_repository,
        evidence_packet_id=payload.evidence_packet_id,
        action_family=payload.action_family,
        proposal_id=payload.proposal_id,
        proposal_version_no=payload.proposal_version_no,
        audience=payload.audience,
        policy_evaluations=list(policy_evaluations),
    )
    record = save_advisory_copilot_evidence_packet(
        repository=repository,
        evidence_packet=packet,
        audience=payload.audience,
        created_by=payload.created_by,
        reason={
            **payload.reason,
            "source_projection": "PROPOSAL_VERSION",
            "proposal_id": payload.proposal_id,
            "proposal_version_no": payload.proposal_version_no,
        },
        correlation_id=resolve_advisory_copilot_correlation_id(
            correlation_id,
            fallback=f"corr-{packet.evidence_packet_id}",
        ),
    )
    return AdvisoryCopilotEvidencePacketResponse(evidence_packet=packet, record=record)
