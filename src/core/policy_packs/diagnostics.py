from __future__ import annotations

from typing import Any

from src.core.policy_packs.persistence import (
    get_policy_evaluation_record,
    list_policy_evaluation_events,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationAuditEvent
from src.core.policy_packs.projection_models import PolicyEvaluationDiagnosticsResponse
from src.core.policy_packs.workflow import get_policy_evaluation_workflow

_DIAGNOSTICS_CONTRACT_VERSION = "policy-evaluation-diagnostics.v1"
_RUNBOOK_REF = "wiki/Operations-Runbook.md#policy-evaluation-diagnostics"


def get_policy_evaluation_diagnostics(
    *,
    evaluation_id: str,
) -> PolicyEvaluationDiagnosticsResponse:
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    events = list_policy_evaluation_events(evaluation_id=evaluation_id)
    workflow = get_policy_evaluation_workflow(evaluation_id=evaluation_id)
    latest_review = _latest_event(events, "POLICY_EVALUATION_REVIEW_RECORDED")
    latest_sign_off = _latest_event(events, "POLICY_EVALUATION_SIGN_OFF_RECORDED")
    latest_report = _latest_event(events, "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED")
    latest_ai = _latest_event(events, "POLICY_EVALUATION_AI_EVIDENCE_RECORDED")
    return PolicyEvaluationDiagnosticsResponse(
        evaluation_id=record.evaluation_id,
        proposal_id=record.proposal_id,
        evaluation_status=record.evaluation_status,
        sign_off_status=workflow.sign_off_status,
        latest_events={
            "review": _event_summary(latest_review),
            "sign_off": _event_summary(latest_sign_off),
            "report_package": _event_summary(latest_report),
            "ai_evidence": _event_summary(latest_ai),
        },
        report_package_posture=_report_package_posture(
            latest_report=latest_report,
            signed_off=workflow.sign_off_status == "SIGNED_OFF" and not workflow.sign_off_blockers,
        ),
        ai_evidence_posture=_ai_evidence_posture(latest_ai=latest_ai),
        replay_posture={
            "evaluation_hash": record.evaluation_hash,
            "source_evidence_hash": record.source_evidence_hash,
            "policy_content_hash": record.policy_content_hash,
            "idempotency_key": record.replay_metadata_json.get("idempotency_key"),
            "replay_policy": record.replay_metadata_json.get("replay_policy"),
        },
        safe_next_action=_safe_next_action(
            sign_off_status=workflow.sign_off_status,
            sign_off_blockers=workflow.sign_off_blockers,
            latest_report=latest_report,
            latest_ai=latest_ai,
        ),
        runbook_ref=_RUNBOOK_REF,
        diagnostics_contract_version=_DIAGNOSTICS_CONTRACT_VERSION,
    )


def _latest_event(
    events: list[PolicyEvaluationAuditEvent],
    event_type: str,
) -> PolicyEvaluationAuditEvent | None:
    matching = [event for event in events if event.event_type == event_type]
    return matching[-1] if matching else None


def _event_summary(event: PolicyEvaluationAuditEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "actor_id": event.actor_id,
        "idempotency_key_present": bool(event.idempotency_key),
    }


def _report_package_posture(
    *,
    latest_report: PolicyEvaluationAuditEvent | None,
    signed_off: bool,
) -> dict[str, Any]:
    if latest_report is None:
        return {
            "status": "NO_REPORT_REQUEST",
            "downstream_owner": "lotus-report",
            "report_request_id": None,
            "report_package_id": None,
            "render_present": False,
            "archive_present": False,
            "replay_eligible": signed_off,
        }
    reason = latest_report.reason_json
    return {
        "status": reason.get("report_package_status") or "RECORDED",
        "downstream_owner": "lotus-report",
        "report_request_id": reason.get("report_request_id"),
        "report_package_id": reason.get("report_package_id"),
        "render_present": bool(reason.get("render")),
        "archive_present": bool(reason.get("archive")),
        "replay_eligible": True,
    }


def _ai_evidence_posture(
    *,
    latest_ai: PolicyEvaluationAuditEvent | None,
) -> dict[str, Any]:
    if latest_ai is None:
        return {
            "status": "NO_AI_EVIDENCE_REQUEST",
            "downstream_owner": "lotus-ai",
            "fallback_reason": None,
            "human_review_required": True,
        }
    reason = latest_ai.reason_json
    lineage_value = reason.get("lineage")
    lineage = lineage_value if isinstance(lineage_value, dict) else {}
    return {
        "status": reason.get("ai_status") or "UNAVAILABLE",
        "downstream_owner": "lotus-ai",
        "fallback_reason": lineage.get("fallback_reason"),
        "human_review_required": True,
    }


def _safe_next_action(
    *,
    sign_off_status: str,
    sign_off_blockers: list[str],
    latest_report: PolicyEvaluationAuditEvent | None,
    latest_ai: PolicyEvaluationAuditEvent | None,
) -> str:
    if sign_off_status != "SIGNED_OFF" or sign_off_blockers:
        return "RESOLVE_POLICY_SIGN_OFF_BLOCKERS"
    if latest_report is None:
        return "REQUEST_POLICY_REPORT_PACKAGE"
    if latest_ai is None:
        return "REQUEST_POLICY_AI_EVIDENCE_IF_OPERATOR_NEEDS_EXPLANATION"
    return "MONITOR_RECORDED_POLICY_EVIDENCE"
