from typing import Any, Optional

from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.replay.models import (
    AdvisoryReplayContinuity,
    AdvisoryReplayEvidenceResponse,
    AdvisoryReplayHashes,
    AdvisoryReplayResolvedContext,
    AdvisoryReplaySubject,
)
from src.core.workspace.models import WorkspaceSavedVersion, WorkspaceSession


def build_workspace_saved_version_replay_response(
    *,
    session: WorkspaceSession,
    saved_version: WorkspaceSavedVersion,
) -> AdvisoryReplayEvidenceResponse:
    continuity = saved_version.replay_evidence.continuity
    return AdvisoryReplayEvidenceResponse(
        subject=AdvisoryReplaySubject(
            scope="WORKSPACE_SAVED_VERSION",
            workspace_id=session.workspace_id,
            workspace_version_id=saved_version.workspace_version_id,
            proposal_id=_optional_str(continuity.get("proposal_id")),
            proposal_version_no=_optional_int(continuity.get("proposal_version_no")),
        ),
        resolved_context=_to_replay_resolved_context(
            saved_version.replay_evidence.resolved_context
        ),
        hashes=AdvisoryReplayHashes(
            evaluation_request_hash=saved_version.replay_evidence.evaluation_request_hash,
            draft_state_hash=saved_version.replay_evidence.draft_state_hash,
        ),
        continuity=AdvisoryReplayContinuity(
            workspace_version_id=saved_version.workspace_version_id,
            handoff_action=_optional_str(continuity.get("handoff_action")),
            handoff_at=_optional_str(continuity.get("handoff_at")),
            handoff_by=_optional_str(continuity.get("handoff_by")),
            source_workspace_id=session.workspace_id,
            lifecycle_origin="WORKSPACE_HANDOFF"
            if continuity.get("proposal_id") is not None
            else None,
        ),
        evidence={
            "saved_at": saved_version.saved_at,
            "saved_by": saved_version.saved_by,
            "version_number": saved_version.version_number,
            "version_label": saved_version.version_label,
            "risk_lens": saved_version.replay_evidence.risk_lens,
        },
        explanation={
            "source": "WORKSPACE_SAVED_VERSION",
            "continuity_status": (
                "LINKED_TO_PROPOSAL_LIFECYCLE"
                if continuity.get("proposal_id") is not None
                else "WORKSPACE_ONLY_REPLAY_EVIDENCE"
            ),
        },
    )


def build_proposal_version_replay_response(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    events: list[ProposalWorkflowEventRecord],
) -> AdvisoryReplayEvidenceResponse:
    context_resolution = version.evidence_bundle_json.get("context_resolution", {})
    replay_lineage = version.evidence_bundle_json.get("replay_lineage", {})
    delivery_summary = _build_delivery_summary(events=events)
    return AdvisoryReplayEvidenceResponse(
        subject=AdvisoryReplaySubject(
            scope="PROPOSAL_VERSION",
            workspace_id=_optional_str(replay_lineage.get("workspace_id"))
            or proposal.source_workspace_id,
            workspace_version_id=_optional_str(replay_lineage.get("workspace_version_id")),
            proposal_id=proposal.proposal_id,
            proposal_version_id=version.proposal_version_id,
            proposal_version_no=version.version_no,
            operation_id=_optional_str(replay_lineage.get("async_operation_id")),
        ),
        resolved_context=_to_replay_resolved_context(context_resolution.get("resolved_context")),
        hashes=AdvisoryReplayHashes(
            request_hash=version.request_hash,
            evaluation_request_hash=_optional_str(replay_lineage.get("evaluation_request_hash")),
            draft_state_hash=_optional_str(replay_lineage.get("draft_state_hash")),
            simulation_hash=version.simulation_hash,
            artifact_hash=version.artifact_hash,
        ),
        continuity=AdvisoryReplayContinuity(
            lifecycle_origin=proposal.lifecycle_origin,
            source_workspace_id=proposal.source_workspace_id,
            workspace_version_id=_optional_str(replay_lineage.get("workspace_version_id")),
            handoff_action=_optional_str(replay_lineage.get("handoff_action")),
            handoff_at=_optional_str(replay_lineage.get("handoff_at")),
            handoff_by=_optional_str(replay_lineage.get("handoff_by")),
            async_operation_id=_optional_str(replay_lineage.get("async_operation_id")),
            async_operation_type=_optional_str(replay_lineage.get("async_operation_type")),
            correlation_id=_optional_str(replay_lineage.get("correlation_id")),
            idempotency_key=_optional_str(replay_lineage.get("idempotency_key")),
        ),
        evidence={
            "context_resolution": context_resolution,
            "replay_lineage": replay_lineage,
            "risk_lens": version.evidence_bundle_json.get("risk_lens"),
            "delivery": delivery_summary,
        },
        explanation={
            "source": "PROPOSAL_VERSION_EVIDENCE_BUNDLE",
            "continuity_status": (
                "WORKSPACE_AND_ASYNC_LINKED" if replay_lineage else "PROPOSAL_ONLY_REPLAY_EVIDENCE"
            ),
        },
    )


def build_async_operation_replay_response(
    *,
    operation: ProposalAsyncOperationRecord,
    proposal: Optional[ProposalRecord],
    version: Optional[ProposalVersionRecord],
    events: list[ProposalWorkflowEventRecord] | None = None,
) -> AdvisoryReplayEvidenceResponse:
    proposal_replay = (
        build_proposal_version_replay_response(
            proposal=proposal,
            version=version,
            events=events or [],
        )
        if proposal is not None and version is not None
        else None
    )
    if proposal_replay is not None:
        subject = proposal_replay.subject.model_copy(
            update={
                "scope": "ASYNC_OPERATION",
                "operation_id": operation.operation_id,
            }
        )
        continuity = proposal_replay.continuity.model_copy(
            update={
                "async_operation_id": operation.operation_id,
                "async_operation_type": operation.operation_type,
                "correlation_id": operation.correlation_id,
                "idempotency_key": operation.idempotency_key,
            }
        )
        evidence = dict(proposal_replay.evidence)
        evidence["async_runtime"] = {
            "status": operation.status,
            "attempt_count": operation.attempt_count,
            "max_attempts": operation.max_attempts,
            "created_at": operation.created_at.isoformat(),
            "started_at": operation.started_at.isoformat() if operation.started_at else None,
            "finished_at": operation.finished_at.isoformat() if operation.finished_at else None,
        }
        explanation = dict(proposal_replay.explanation)
        explanation["source"] = "ASYNC_OPERATION_AND_PROPOSAL_VERSION"
        return AdvisoryReplayEvidenceResponse(
            subject=subject,
            resolved_context=proposal_replay.resolved_context,
            hashes=proposal_replay.hashes,
            continuity=continuity,
            evidence=evidence,
            explanation=explanation,
        )

    return AdvisoryReplayEvidenceResponse(
        subject=AdvisoryReplaySubject(
            scope="ASYNC_OPERATION",
            proposal_id=operation.proposal_id,
            operation_id=operation.operation_id,
        ),
        resolved_context=None,
        hashes=AdvisoryReplayHashes(),
        continuity=AdvisoryReplayContinuity(
            async_operation_id=operation.operation_id,
            async_operation_type=operation.operation_type,
            correlation_id=operation.correlation_id,
            idempotency_key=operation.idempotency_key,
        ),
        evidence={
            "async_runtime": {
                "status": operation.status,
                "attempt_count": operation.attempt_count,
                "max_attempts": operation.max_attempts,
                "created_at": operation.created_at.isoformat(),
                "started_at": operation.started_at.isoformat() if operation.started_at else None,
                "finished_at": operation.finished_at.isoformat() if operation.finished_at else None,
                "payload_json": operation.payload_json,
                "error": operation.error_json,
            }
        },
        explanation={
            "source": "ASYNC_OPERATION_ONLY",
            "continuity_status": "NO_TERMINAL_PROPOSAL_VERSION_AVAILABLE",
        },
    )


def _to_replay_resolved_context(
    raw_context: Any,
) -> AdvisoryReplayResolvedContext | None:
    if raw_context is None:
        return None
    if hasattr(raw_context, "model_dump"):
        data = raw_context.model_dump(mode="json")
    elif isinstance(raw_context, dict):
        data = raw_context
    else:
        return None
    if data.get("portfolio_id") is None or data.get("as_of") is None:
        return None
    context: AdvisoryReplayResolvedContext = AdvisoryReplayResolvedContext.model_validate(data)
    return context


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _build_delivery_summary(
    *,
    events: list[ProposalWorkflowEventRecord],
) -> dict[str, Any]:
    latest_execution_requested: ProposalWorkflowEventRecord | None = None
    latest_execution_event: ProposalWorkflowEventRecord | None = None
    latest_report_request: ProposalWorkflowEventRecord | None = None
    execution_event_types = {
        "EXECUTION_REQUESTED",
        "EXECUTION_ACCEPTED",
        "EXECUTION_PARTIALLY_EXECUTED",
        "EXECUTION_REJECTED",
        "EXECUTION_CANCELLED",
        "EXECUTION_EXPIRED",
        "EXECUTED",
    }
    for event in events:
        if event.event_type == "EXECUTION_REQUESTED":
            latest_execution_requested = event
        if event.event_type in execution_event_types:
            latest_execution_event = event
        if event.event_type == "REPORT_REQUESTED":
            latest_report_request = event

    execution: dict[str, Any] | None = None
    if latest_execution_requested is not None or latest_execution_event is not None:
        target_event = latest_execution_event or latest_execution_requested
        assert target_event is not None
        event_type_to_status = {
            "EXECUTION_REQUESTED": "REQUESTED",
            "EXECUTION_ACCEPTED": "ACCEPTED",
            "EXECUTION_PARTIALLY_EXECUTED": "PARTIALLY_EXECUTED",
            "EXECUTION_REJECTED": "REJECTED",
            "EXECUTION_CANCELLED": "CANCELLED",
            "EXECUTION_EXPIRED": "EXPIRED",
            "EXECUTED": "EXECUTED",
        }
        execution = {
            "handoff_status": event_type_to_status[target_event.event_type],
            "execution_request_id": _optional_str(
                target_event.reason_json.get("execution_request_id")
                if target_event.reason_json.get("execution_request_id") is not None
                else (
                    latest_execution_requested.reason_json.get("execution_request_id")
                    if latest_execution_requested is not None
                    else None
                )
            ),
            "execution_provider": _optional_str(
                target_event.reason_json.get("execution_provider")
                if target_event.reason_json.get("execution_provider") is not None
                else (
                    latest_execution_requested.reason_json.get("execution_provider")
                    if latest_execution_requested is not None
                    else None
                )
            ),
            "related_version_no": target_event.related_version_no,
            "handoff_requested_at": (
                latest_execution_requested.occurred_at.isoformat()
                if latest_execution_requested is not None
                else None
            ),
            "executed_at": (
                target_event.occurred_at.isoformat()
                if target_event.event_type == "EXECUTED"
                else None
            ),
            "latest_event_type": target_event.event_type,
            "external_execution_id": _optional_str(
                target_event.reason_json.get("external_execution_id")
            ),
        }

    reporting: dict[str, Any] | None = None
    if latest_report_request is not None:
        reporting = {
            "report_request_id": _optional_str(
                latest_report_request.reason_json.get("report_request_id")
            ),
            "report_type": _optional_str(latest_report_request.reason_json.get("report_type")),
            "report_service": _optional_str(
                latest_report_request.reason_json.get("report_service")
            ),
            "status": _optional_str(latest_report_request.reason_json.get("status")),
            "report_reference_id": _optional_str(
                latest_report_request.reason_json.get("report_reference_id")
            ),
            "artifact_url": _optional_str(latest_report_request.reason_json.get("artifact_url")),
            "requested_by": latest_report_request.actor_id,
            "related_version_no": latest_report_request.related_version_no,
            "include_execution_summary": latest_report_request.reason_json.get(
                "include_execution_summary"
            ),
            "generated_at": latest_report_request.occurred_at.isoformat(),
        }

    return {
        "execution": execution,
        "reporting": reporting,
    }
