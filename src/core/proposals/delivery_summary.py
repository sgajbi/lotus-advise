from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.proposals.execution_boundary import execution_ownership_boundary
from src.core.proposals.models import (
    ProposalDeliveryExecutionSummary,
    ProposalDeliveryHistoryResponse,
    ProposalDeliveryReportingSummary,
    ProposalDeliverySummaryResponse,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.projections import to_proposal_summary, to_workflow_event
from src.core.proposals.workflow_rules import (
    EXECUTION_STATUS_EVENT_TYPES,
    execution_status_for_event,
)

_DELIVERY_EVENT_TYPES = EXECUTION_STATUS_EVENT_TYPES | {"REPORT_REQUESTED"}


@dataclass(frozen=True)
class _LatestDeliveryEvents:
    execution_requested: ProposalWorkflowEventRecord | None = None
    execution_status: ProposalWorkflowEventRecord | None = None
    report_request: ProposalWorkflowEventRecord | None = None


def build_delivery_summary_from_events(
    events: list[ProposalWorkflowEventRecord],
) -> dict[str, Any]:
    latest = _latest_delivery_events(events)
    return {
        "execution": _build_execution_summary(latest),
        "reporting": _build_reporting_summary(latest.report_request),
    }


def _latest_delivery_events(events: list[ProposalWorkflowEventRecord]) -> _LatestDeliveryEvents:
    execution_requested: ProposalWorkflowEventRecord | None = None
    execution_status: ProposalWorkflowEventRecord | None = None
    report_request: ProposalWorkflowEventRecord | None = None
    for event in events:
        if event.event_type == "EXECUTION_REQUESTED":
            execution_requested = event
        if event.event_type in EXECUTION_STATUS_EVENT_TYPES:
            execution_status = event
        if event.event_type == "REPORT_REQUESTED":
            report_request = event
    return _LatestDeliveryEvents(
        execution_requested=execution_requested,
        execution_status=execution_status,
        report_request=report_request,
    )


def _build_execution_summary(latest: _LatestDeliveryEvents) -> dict[str, Any] | None:
    target_event = latest.execution_status or latest.execution_requested
    if target_event is None:
        return None
    return {
        "handoff_status": execution_status_for_event(target_event.event_type),
        "execution_request_id": _event_reason_str(
            target_event, "execution_request_id", fallback=latest.execution_requested
        ),
        "execution_provider": _event_reason_str(
            target_event, "execution_provider", fallback=latest.execution_requested
        ),
        "related_version_no": target_event.related_version_no,
        "handoff_requested_at": _event_occurred_at(latest.execution_requested),
        "executed_at": (
            target_event.occurred_at.isoformat() if target_event.event_type == "EXECUTED" else None
        ),
        "latest_event_type": target_event.event_type,
        "external_execution_id": _event_reason_str(target_event, "external_execution_id"),
        "execution_ownership": execution_ownership_boundary(),
    }


def _build_reporting_summary(
    report_request: ProposalWorkflowEventRecord | None,
) -> dict[str, Any] | None:
    if report_request is None:
        return None
    return {
        "report_request_id": _event_reason_str(report_request, "report_request_id"),
        "report_type": _event_reason_str(report_request, "report_type"),
        "report_service": _event_reason_str(report_request, "report_service"),
        "status": _event_reason_str(report_request, "status"),
        "report_reference_id": _event_reason_str(report_request, "report_reference_id"),
        "artifact_url": _event_reason_str(report_request, "artifact_url"),
        "requested_by": report_request.actor_id,
        "related_version_no": report_request.related_version_no,
        "include_execution_summary": report_request.reason_json.get("include_execution_summary"),
        "include_reviewed_narrative": report_request.reason_json.get(
            "include_reviewed_narrative", False
        ),
        "proposal_narrative_package": report_request.reason_json.get("proposal_narrative_package"),
        "generated_at": report_request.occurred_at.isoformat(),
    }


def select_delivery_events(
    events: list[ProposalWorkflowEventRecord],
) -> list[ProposalWorkflowEventRecord]:
    return [event for event in events if event.event_type in _DELIVERY_EVENT_TYPES]


def build_delivery_summary_response(
    *,
    proposal: ProposalRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ProposalDeliverySummaryResponse:
    delivery = build_delivery_summary_from_events(events)
    execution_payload = delivery.get("execution")
    reporting_payload = delivery.get("reporting")
    return ProposalDeliverySummaryResponse(
        proposal=to_proposal_summary(proposal),
        execution=(
            ProposalDeliveryExecutionSummary.model_validate(execution_payload)
            if isinstance(execution_payload, dict)
            else None
        ),
        reporting=(
            ProposalDeliveryReportingSummary.model_validate(reporting_payload)
            if isinstance(reporting_payload, dict)
            else None
        ),
        explanation={
            "source": "ADVISORY_WORKFLOW_EVENTS",
            "delivery_projection": "LATEST_EXECUTION_AND_REPORTING_POSTURE",
            "execution_ownership": execution_ownership_boundary(),
        },
    )


def build_delivery_history_response(
    *,
    proposal: ProposalRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ProposalDeliveryHistoryResponse:
    history_events = [to_workflow_event(event) for event in select_delivery_events(events)]
    return ProposalDeliveryHistoryResponse(
        proposal=to_proposal_summary(proposal),
        event_count=len(history_events),
        latest_event=history_events[-1] if history_events else None,
        events=history_events,
        explanation={
            "source": "ADVISORY_WORKFLOW_EVENTS",
            "filter": "DELIVERY_ONLY",
            "execution_ownership": execution_ownership_boundary(),
        },
    )


def _event_reason_str(
    event: ProposalWorkflowEventRecord,
    key: str,
    *,
    fallback: ProposalWorkflowEventRecord | None = None,
) -> str | None:
    value = event.reason_json.get(key)
    if value is None and fallback is not None:
        value = fallback.reason_json.get(key)
    return _optional_str(value)


def _event_occurred_at(event: ProposalWorkflowEventRecord | None) -> str | None:
    return event.occurred_at.isoformat() if event is not None else None


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
