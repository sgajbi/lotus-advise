from __future__ import annotations

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


def build_delivery_summary_from_events(
    events: list[ProposalWorkflowEventRecord],
) -> dict[str, Any]:
    latest_execution_requested: ProposalWorkflowEventRecord | None = None
    latest_execution_event: ProposalWorkflowEventRecord | None = None
    latest_report_request: ProposalWorkflowEventRecord | None = None

    for event in events:
        if event.event_type == "EXECUTION_REQUESTED":
            latest_execution_requested = event
        if event.event_type in EXECUTION_STATUS_EVENT_TYPES:
            latest_execution_event = event
        if event.event_type == "REPORT_REQUESTED":
            latest_report_request = event

    execution: dict[str, Any] | None = None
    if latest_execution_requested is not None or latest_execution_event is not None:
        target_event = latest_execution_event or latest_execution_requested
        if target_event is not None:
            execution = {
                "handoff_status": execution_status_for_event(target_event.event_type),
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
                "execution_ownership": execution_ownership_boundary(),
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
            "include_reviewed_narrative": latest_report_request.reason_json.get(
                "include_reviewed_narrative", False
            ),
            "proposal_narrative_package": latest_report_request.reason_json.get(
                "proposal_narrative_package"
            ),
            "generated_at": latest_report_request.occurred_at.isoformat(),
        }

    return {
        "execution": execution,
        "reporting": reporting,
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


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
