from collections.abc import Sequence
from typing import Any

from src.core.proposals.models import (
    ProposalApprovalRecord,
    ProposalApprovalRecordData,
    ProposalApprovalsResponse,
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationRecord,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateResponse,
    ProposalIdempotencyLookupResponse,
    ProposalIdempotencyRecord,
    ProposalLineageResponse,
    ProposalRecord,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalVersionLineageItem,
    ProposalVersionRecord,
    ProposalWorkflowEvent,
    ProposalWorkflowEventRecord,
    ProposalWorkflowTimelineResponse,
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


def to_create_response(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    latest_event: ProposalWorkflowEventRecord,
) -> ProposalCreateResponse:
    return ProposalCreateResponse(
        proposal=to_proposal_summary(proposal),
        version=to_version_detail(version, include_evidence=True),
        latest_workflow_event=to_workflow_event(latest_event),
    )


def to_idempotency_lookup_response(
    record: ProposalIdempotencyRecord,
) -> ProposalIdempotencyLookupResponse:
    return ProposalIdempotencyLookupResponse(
        idempotency_key=record.idempotency_key,
        request_hash=record.request_hash,
        proposal_id=record.proposal_id,
        proposal_version_no=record.proposal_version_no,
        created_at=record.created_at.isoformat(),
    )


def build_proposal_lineage_response(
    *,
    proposal: ProposalRecord,
    versions_by_number: dict[int, ProposalVersionRecord | None],
) -> ProposalLineageResponse:
    versions: list[ProposalVersionLineageItem] = []
    missing_version_numbers: list[int] = []
    for version_no in range(1, proposal.current_version_no + 1):
        version = versions_by_number.get(version_no)
        if version is None:
            missing_version_numbers.append(version_no)
            continue
        versions.append(
            ProposalVersionLineageItem(
                proposal_version_id=version.proposal_version_id,
                version_no=version.version_no,
                created_at=version.created_at.isoformat(),
                status_at_creation=version.status_at_creation,
                request_hash=version.request_hash,
                simulation_hash=version.simulation_hash,
                artifact_hash=version.artifact_hash,
            )
        )

    latest_version = versions[-1] if versions else None
    return ProposalLineageResponse(
        proposal=to_proposal_summary(proposal),
        version_count=len(versions),
        latest_version_no=latest_version.version_no if latest_version is not None else None,
        latest_version_created_at=(
            latest_version.created_at if latest_version is not None else None
        ),
        lineage_complete=not missing_version_numbers,
        missing_version_numbers=missing_version_numbers,
        versions=versions,
    )


def build_workflow_timeline_response(
    *,
    proposal: ProposalRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ProposalWorkflowTimelineResponse:
    timeline_events = [to_workflow_event(event) for event in events]
    return ProposalWorkflowTimelineResponse(
        proposal=to_proposal_summary(proposal),
        current_state=proposal.current_state,
        event_count=len(timeline_events),
        latest_event=timeline_events[-1] if timeline_events else None,
        events=timeline_events,
    )


def build_approvals_response(
    *,
    proposal: ProposalRecord,
    approvals: Sequence[ProposalApprovalRecordData | None],
) -> ProposalApprovalsResponse:
    projected_approvals = [
        approval
        for approval in (to_approval_record(approval) for approval in approvals)
        if approval is not None
    ]
    latest_approval = projected_approvals[-1] if projected_approvals else None
    return ProposalApprovalsResponse(
        proposal=to_proposal_summary(proposal),
        approval_count=len(projected_approvals),
        latest_approval_at=latest_approval.occurred_at if latest_approval is not None else None,
        approvals=projected_approvals,
    )


def to_async_accepted_response(
    operation: ProposalAsyncOperationRecord,
) -> ProposalAsyncAcceptedResponse:
    return ProposalAsyncAcceptedResponse(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        status=operation.status,
        correlation_id=operation.correlation_id,
        created_at=operation.created_at.isoformat(),
        attempt_count=operation.attempt_count,
        max_attempts=operation.max_attempts,
        status_url=f"/advisory/proposals/operations/{operation.operation_id}",
    )


def to_async_status_response(
    operation: ProposalAsyncOperationRecord,
) -> ProposalAsyncOperationStatusResponse:
    return ProposalAsyncOperationStatusResponse(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        status=operation.status,
        correlation_id=operation.correlation_id,
        idempotency_key=operation.idempotency_key,
        proposal_id=operation.proposal_id,
        created_by=operation.created_by,
        created_at=operation.created_at.isoformat(),
        started_at=(operation.started_at.isoformat() if operation.started_at else None),
        finished_at=(operation.finished_at.isoformat() if operation.finished_at else None),
        attempt_count=operation.attempt_count,
        max_attempts=operation.max_attempts,
        lease_expires_at=(
            operation.lease_expires_at.isoformat() if operation.lease_expires_at else None
        ),
        result=(
            ProposalCreateResponse.model_validate(operation.result_json)
            if operation.result_json is not None
            else None
        ),
        error=operation.error_json,
    )
