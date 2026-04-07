from __future__ import annotations

from typing import Any

from src.core.proposals.models import ProposalWorkflowEventRecord

_EXECUTION_EVENT_TYPES = {
    "EXECUTION_REQUESTED",
    "EXECUTION_ACCEPTED",
    "EXECUTION_PARTIALLY_EXECUTED",
    "EXECUTION_REJECTED",
    "EXECUTION_CANCELLED",
    "EXECUTION_EXPIRED",
    "EXECUTED",
}

_DELIVERY_EVENT_TYPES = _EXECUTION_EVENT_TYPES | {"REPORT_REQUESTED"}


def build_delivery_summary_from_events(
    events: list[ProposalWorkflowEventRecord],
) -> dict[str, Any]:
    latest_execution_requested: ProposalWorkflowEventRecord | None = None
    latest_execution_event: ProposalWorkflowEventRecord | None = None
    latest_report_request: ProposalWorkflowEventRecord | None = None

    for event in events:
        if event.event_type == "EXECUTION_REQUESTED":
            latest_execution_requested = event
        if event.event_type in _EXECUTION_EVENT_TYPES:
            latest_execution_event = event
        if event.event_type == "REPORT_REQUESTED":
            latest_report_request = event

    execution: dict[str, Any] | None = None
    if latest_execution_requested is not None or latest_execution_event is not None:
        target_event = latest_execution_event or latest_execution_requested
        assert target_event is not None
        execution = {
            "handoff_status": _execution_event_to_status(target_event.event_type),
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


def select_delivery_events(
    events: list[ProposalWorkflowEventRecord],
) -> list[ProposalWorkflowEventRecord]:
    return [event for event in events if event.event_type in _DELIVERY_EVENT_TYPES]


def _execution_event_to_status(event_type: str) -> str:
    mapping = {
        "EXECUTION_REQUESTED": "REQUESTED",
        "EXECUTION_ACCEPTED": "ACCEPTED",
        "EXECUTION_PARTIALLY_EXECUTED": "PARTIALLY_EXECUTED",
        "EXECUTION_REJECTED": "REJECTED",
        "EXECUTION_CANCELLED": "CANCELLED",
        "EXECUTION_EXPIRED": "EXPIRED",
        "EXECUTED": "EXECUTED",
    }
    return mapping[event_type]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
