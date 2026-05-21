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

    handoff_status = "NOT_REQUESTED"
    execution_request_id: str | None = None
    execution_provider: str | None = None
    related_version_no: int | None = None
    handoff_requested_at: str | None = None
    executed_at: str | None = None
    external_execution_id: str | None = None
    if latest_execution_requested is not None:
        handoff_status = "REQUESTED"
        execution_request_id = cast(
            str | None,
            latest_execution_requested.reason_json.get("execution_request_id"),
        )
        execution_provider = cast(
            str | None,
            latest_execution_requested.reason_json.get("execution_provider"),
        )
        related_version_no = latest_execution_requested.related_version_no
        handoff_requested_at = latest_execution_requested.occurred_at.isoformat()

    if latest_execution_event is not None:
        handoff_status = execution_status_for_event(latest_execution_event.event_type)
        if latest_execution_event.event_type == "EXECUTED":
            executed_at = latest_execution_event.occurred_at.isoformat()
        external_execution_id = _first_present_string(
            latest_execution_event.reason_json.get("external_execution_id"),
            latest_execution_event.reason_json.get("execution_id"),
        )
        related_version_no = latest_execution_event.related_version_no or related_version_no
        if latest_execution_requested is None:
            execution_request_id = cast(
                str | None,
                latest_execution_event.reason_json.get("execution_request_id"),
            )
            execution_provider = cast(
                str | None,
                latest_execution_event.reason_json.get("execution_provider"),
            )

    return ProposalExecutionStatusResponse(
        proposal=to_proposal_summary(proposal),
        handoff_status=handoff_status,
        execution_request_id=execution_request_id,
        execution_provider=execution_provider,
        related_version_no=related_version_no,
        handoff_requested_at=handoff_requested_at,
        executed_at=executed_at,
        external_execution_id=external_execution_id,
        latest_workflow_event=(
            to_workflow_event(latest_execution_event)
            if latest_execution_event is not None
            else None
        ),
        explanation={
            "source": "ADVISORY_WORKFLOW_EVENTS",
            "state_correlation": execution_state_correlation(handoff_status=handoff_status),
            "execution_ownership": execution_ownership_boundary(),
        },
    )


def _first_present_string(*values: Any) -> str | None:
    for value in values:
        if value is not None:
            return cast(str, value)
    return None
