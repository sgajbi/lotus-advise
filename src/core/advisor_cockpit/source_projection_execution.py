from src.core.advisor_cockpit.action_sources import (
    ExecutionHandoffReadyActionSource,
    ExecutionStatusAttentionActionSource,
)
from src.core.proposals.models import ProposalRecord, ProposalWorkflowEventRecord
from src.core.proposals.workflow_rules import execution_status_for_event


def build_execution_handoff_sources(
    *,
    records: list[ProposalRecord],
    events: dict[str, list[ProposalWorkflowEventRecord]],
) -> list[ExecutionHandoffReadyActionSource]:
    return [
        source
        for record in records
        if (
            source := _execution_handoff_source(
                proposal=record,
                events=events.get(record.proposal_id, []),
            )
        )
        is not None
    ]


def build_execution_status_sources(
    *,
    proposals: dict[str, ProposalRecord],
    events: dict[str, list[ProposalWorkflowEventRecord]],
) -> list[ExecutionStatusAttentionActionSource]:
    return [
        source
        for proposal_id, proposal_events in events.items()
        if (
            source := _execution_status_source(
                proposal=proposals.get(proposal_id),
                events=proposal_events,
            )
        )
        is not None
    ]


def _execution_handoff_source(
    *,
    proposal: ProposalRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ExecutionHandoffReadyActionSource | None:
    if proposal.current_state != "EXECUTION_READY":
        return None
    if any(event.event_type == "EXECUTION_REQUESTED" for event in events):
        return None
    return ExecutionHandoffReadyActionSource(
        handoff_id=f"execution_handoff_ready_{proposal.proposal_id}",
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        source_timestamp=proposal.last_event_at.isoformat(),
        materiality_rank=62,
    )


def _execution_status_source(
    *,
    proposal: ProposalRecord | None,
    events: list[ProposalWorkflowEventRecord],
) -> ExecutionStatusAttentionActionSource | None:
    if proposal is None:
        return None
    latest_event = _latest_execution_event(events)
    if latest_event is None or latest_event.event_type == "EXECUTED":
        return None
    handoff_status = execution_status_for_event(latest_event.event_type)
    if handoff_status == "NOT_REQUESTED":
        return None
    execution_ref = str(
        latest_event.reason_json.get("execution_request_id")
        or latest_event.reason_json.get("external_execution_id")
        or latest_event.event_id
    )
    return ExecutionStatusAttentionActionSource(
        execution_ref=execution_ref,
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        handoff_status=handoff_status,
        summary=f"Execution handoff status is {handoff_status}; downstream execution remains SOR.",
        source_timestamp=latest_event.occurred_at.isoformat(),
        materiality_rank=72 if handoff_status in {"REJECTED", "CANCELLED", "EXPIRED"} else 50,
    )


def _latest_execution_event(
    events: list[ProposalWorkflowEventRecord],
) -> ProposalWorkflowEventRecord | None:
    execution_events = [
        event for event in events if execution_status_for_event(event.event_type) != "NOT_REQUESTED"
    ]
    if not execution_events:
        return None
    return sorted(execution_events, key=lambda item: (item.occurred_at, item.event_id))[-1]


__all__ = [
    "build_execution_handoff_sources",
    "build_execution_status_sources",
]
