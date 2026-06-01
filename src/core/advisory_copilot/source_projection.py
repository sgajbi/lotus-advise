from __future__ import annotations

from src.core.advisory_copilot.evidence_packets import build_copilot_evidence_packet
from src.core.advisory_copilot.models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotEvidencePacket,
    CopilotLineageRef,
)
from src.core.advisory_copilot.source_projection_sections import (
    EVIDENCE_PACKET_ID_MAX_LENGTH,
    LINEAGE_REF_ID_MAX_LENGTH,
    bounded_projection_reference,
    build_proposal_version_source_sections,
    default_proposal_version_packet_id,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.repository import ProposalRepository


def build_proposal_version_copilot_evidence_packet(
    *,
    repository: ProposalRepository,
    evidence_packet_id: str | None,
    action_family: CopilotActionFamily,
    proposal_id: str,
    proposal_version_no: int,
    audience: CopilotAudience,
    policy_evaluations: list[PolicyEvaluationRecord],
) -> CopilotEvidencePacket:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    version = repository.get_version(
        proposal_id=proposal_id,
        version_no=proposal_version_no,
    )
    if proposal is None or version is None:
        raise ValueError("COPILOT_PROPOSAL_VERSION_NOT_FOUND")

    memos = repository.list_memos(proposal_id=proposal_id)
    memo = repository.get_memo_by_proposal_version(
        proposal_id=proposal_id,
        proposal_version_no=proposal_version_no,
    )
    approvals = repository.list_approvals(proposal_id=proposal_id)
    events = repository.list_events(proposal_id=proposal_id)
    matching_policy = _policy_evaluations_for_version(
        policy_evaluations=policy_evaluations,
        proposal_id=proposal_id,
        proposal_version_id=version.proposal_version_id,
    )
    source_sections = build_proposal_version_source_sections(
        proposal=proposal,
        version=version,
        memo=memo,
        memos=memos,
        approvals=approvals,
        events=events,
        policy_evaluations=matching_policy,
    )
    packet_id = (
        bounded_projection_reference(
            evidence_packet_id,
            max_length=EVIDENCE_PACKET_ID_MAX_LENGTH,
        )
        if evidence_packet_id
        else default_proposal_version_packet_id(
            action_family=action_family,
            proposal_id=proposal_id,
            version_no=proposal_version_no,
        )
    )
    return build_copilot_evidence_packet(
        evidence_packet_id=packet_id,
        action_family=action_family,
        portfolio_id=proposal.portfolio_id,
        proposal_id=proposal.proposal_id,
        audience=audience,
        source_sections=tuple(source_sections),
        lineage_refs=(
            CopilotLineageRef(
                lineage_type="PROPOSAL_VERSION",
                lineage_id=bounded_projection_reference(
                    version.proposal_version_id,
                    max_length=LINEAGE_REF_ID_MAX_LENGTH,
                ),
                source_system="lotus-advise",
            ),
            CopilotLineageRef(
                lineage_type="PROPOSAL_VERSION_NO",
                lineage_id=str(version.version_no),
                source_system="lotus-advise",
            ),
        ),
    )


def _policy_evaluations_for_version(
    *,
    policy_evaluations: list[PolicyEvaluationRecord],
    proposal_id: str,
    proposal_version_id: str,
) -> list[PolicyEvaluationRecord]:
    return [
        record
        for record in policy_evaluations
        if record.proposal_id == proposal_id and record.proposal_version_id == proposal_version_id
    ]
