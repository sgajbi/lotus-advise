from dataclasses import dataclass, replace
from typing import Any, cast

from src.core.proposals.execution_boundary import execution_ownership_boundary
from src.core.proposals.models import (
    ProposalExecutionStatusResponse,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.projections import to_proposal_summary, to_workflow_event
from src.core.proposals.workflow_rules import (
    EXECUTION_STATUS_EVENT_TYPES,
    execution_state_correlation,
    execution_status_for_event,
)


@dataclass(frozen=True)
class _ExecutionStatusProjection:
    handoff_status: str = "NOT_REQUESTED"
    execution_request_id: str | None = None
    execution_provider: str | None = None
    related_version_no: int | None = None
    handoff_requested_at: str | None = None
    executed_at: str | None = None
    external_execution_id: str | None = None


def latest_execution_requested_event(
    events: list[ProposalWorkflowEventRecord],
) -> ProposalWorkflowEventRecord | None:
    for event in reversed(events):
        if event.event_type == "EXECUTION_REQUESTED":
            return event
    return None


def latest_execution_status_event(
    events: list[ProposalWorkflowEventRecord],
) -> ProposalWorkflowEventRecord | None:
    for event in reversed(events):
        if event.event_type in EXECUTION_STATUS_EVENT_TYPES:
            return event
    return None


def build_execution_status_response(
    *,
    proposal: ProposalRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ProposalExecutionStatusResponse:
    latest_execution_requested = latest_execution_requested_event(events)
    latest_execution_event = latest_execution_status_event(events)
    projection = _execution_status_projection(
        latest_execution_requested=latest_execution_requested,
        latest_execution_event=latest_execution_event,
    )

    return ProposalExecutionStatusResponse(
        proposal=to_proposal_summary(proposal),
        handoff_status=projection.handoff_status,
        execution_request_id=projection.execution_request_id,
        execution_provider=projection.execution_provider,
        related_version_no=projection.related_version_no,
        handoff_requested_at=projection.handoff_requested_at,
        executed_at=projection.executed_at,
        external_execution_id=projection.external_execution_id,
        latest_workflow_event=(
            to_workflow_event(latest_execution_event)
            if latest_execution_event is not None
            else None
        ),
        explanation={
            "source": "ADVISORY_WORKFLOW_EVENTS",
            "state_correlation": execution_state_correlation(
                handoff_status=projection.handoff_status
            ),
            "execution_ownership": execution_ownership_boundary(),
        },
    )


def _execution_status_projection(
    *,
    latest_execution_requested: ProposalWorkflowEventRecord | None,
    latest_execution_event: ProposalWorkflowEventRecord | None,
) -> _ExecutionStatusProjection:
    projection = _requested_event_projection(latest_execution_requested)
    if latest_execution_event is None:
        return projection
    return _status_event_projection(
        latest_execution_event,
        projection=projection,
        has_request_event=latest_execution_requested is not None,
    )


def _requested_event_projection(
    event: ProposalWorkflowEventRecord | None,
) -> _ExecutionStatusProjection:
    if event is None:
        return _ExecutionStatusProjection()
    return _ExecutionStatusProjection(
        handoff_status="REQUESTED",
        execution_request_id=_event_text(event, "execution_request_id"),
        execution_provider=_event_text(event, "execution_provider"),
        related_version_no=event.related_version_no,
        handoff_requested_at=event.occurred_at.isoformat(),
    )


def _status_event_projection(
    event: ProposalWorkflowEventRecord,
    *,
    projection: _ExecutionStatusProjection,
    has_request_event: bool,
) -> _ExecutionStatusProjection:
    return replace(
        projection,
        handoff_status=execution_status_for_event(event.event_type),
        execution_request_id=_execution_request_id(event, projection, has_request_event),
        execution_provider=_execution_provider(event, projection, has_request_event),
        related_version_no=event.related_version_no or projection.related_version_no,
        executed_at=_executed_at(event),
        external_execution_id=_external_execution_id(event),
    )


def _execution_request_id(
    event: ProposalWorkflowEventRecord,
    projection: _ExecutionStatusProjection,
    has_request_event: bool,
) -> str | None:
    if has_request_event:
        return projection.execution_request_id
    return _event_text(event, "execution_request_id")


def _execution_provider(
    event: ProposalWorkflowEventRecord,
    projection: _ExecutionStatusProjection,
    has_request_event: bool,
) -> str | None:
    if has_request_event:
        return projection.execution_provider
    return _event_text(event, "execution_provider")


def _executed_at(event: ProposalWorkflowEventRecord) -> str | None:
    if event.event_type != "EXECUTED":
        return None
    return event.occurred_at.isoformat()


def _external_execution_id(event: ProposalWorkflowEventRecord) -> str | None:
    return _first_present_string(
        event.reason_json.get("external_execution_id"),
        event.reason_json.get("execution_id"),
    )


def _event_text(event: ProposalWorkflowEventRecord, key: str) -> str | None:
    return cast(str | None, event.reason_json.get(key))


def _first_present_string(*values: Any) -> str | None:
    for value in values:
        if value is not None:
            return cast(str, value)
    return None
