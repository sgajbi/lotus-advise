from typing import Any

from src.core.proposals.models import (
    ProposalApprovalRecord,
    ProposalApprovalRecordData,
    ProposalRecord,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalVersionRecord,
    ProposalWorkflowEvent,
    ProposalWorkflowEventRecord,
)


def to_proposal_summary(proposal: ProposalRecord) -> ProposalSummary:
    return ProposalSummary(
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        mandate_id=proposal.mandate_id,
        jurisdiction=proposal.jurisdiction,
        created_by=proposal.created_by,
        created_at=proposal.created_at.isoformat(),
        last_event_at=proposal.last_event_at.isoformat(),
        current_state=proposal.current_state,
        current_version_no=proposal.current_version_no,
        title=proposal.title,
        lifecycle_origin=proposal.lifecycle_origin,
        source_workspace_id=proposal.source_workspace_id,
    )


def to_version_detail(
    version: ProposalVersionRecord, *, include_evidence: bool
) -> ProposalVersionDetail:
    evidence_bundle_json: dict[str, Any] = version.evidence_bundle_json if include_evidence else {}
    return ProposalVersionDetail(
        proposal_version_id=version.proposal_version_id,
        proposal_id=version.proposal_id,
        version_no=version.version_no,
        created_at=version.created_at.isoformat(),
        request_hash=version.request_hash,
        artifact_hash=version.artifact_hash,
        simulation_hash=version.simulation_hash,
        status_at_creation=version.status_at_creation,
        proposal_result=version.proposal_result_json,
        artifact=version.artifact_json,
        evidence_bundle=evidence_bundle_json,
        gate_decision=version.gate_decision_json,
    )


def to_workflow_event(event: ProposalWorkflowEventRecord) -> ProposalWorkflowEvent:
    return ProposalWorkflowEvent(
        event_id=event.event_id,
        proposal_id=event.proposal_id,
        event_type=event.event_type,
        from_state=event.from_state,
        to_state=event.to_state,
        actor_id=event.actor_id,
        occurred_at=event.occurred_at.isoformat(),
        reason=event.reason_json,
        related_version_no=event.related_version_no,
    )


def to_approval_record(
    approval: ProposalApprovalRecordData | None,
) -> ProposalApprovalRecord | None:
    if approval is None:
        return None
    return ProposalApprovalRecord(
        approval_id=approval.approval_id,
        proposal_id=approval.proposal_id,
        approval_type=approval.approval_type,
        approved=approval.approved,
        actor_id=approval.actor_id,
        occurred_at=approval.occurred_at.isoformat(),
        details=approval.details_json,
        related_version_no=approval.related_version_no,
    )
