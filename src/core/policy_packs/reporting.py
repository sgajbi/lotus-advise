from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast

from src.core.common.canonical import hash_canonical_payload
from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.policy_packs.persistence import (
    append_policy_evaluation_event,
    get_policy_evaluation_record,
    list_policy_evaluation_events,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)
from src.core.policy_packs.reporting_models import (
    PolicyEvaluationReportPackageRequest,
    PolicyEvaluationReportPackageResponse,
)
from src.core.policy_packs.workflow import get_policy_evaluation_workflow
from src.core.proposals.contract_types import ProposalReportType
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalValidationError,
)
from src.core.proposals.models import ProposalReportResponse
from src.integrations.lotus_report import request_policy_sign_off_report_package_with_lotus_report

_REPORTING_CONTRACT_VERSION = "rfc0025.policy-report-package-realization.v1"
_CLIENT_READY_PUBLICATION = "BLOCKED"


def request_policy_evaluation_report_package(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationReportPackageRequest,
    report_request_id: str,
    idempotency_key: str | None = None,
) -> PolicyEvaluationReportPackageResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    _validate_report_request(record=record, payload=payload)

    request_hash = _request_hash(record=record, payload=payload)
    if idempotency_key:
        replayed_event = _find_replayed_report_event(
            evaluation_id=evaluation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed_event is not None:
            return PolicyEvaluationReportPackageResponse(
                evaluation=get_policy_evaluation_record(evaluation_id=evaluation_id),
                report_package_event=replayed_event,
                report=_report_response_from_event(record=record, event=replayed_event),
                replayed=True,
            )

    sign_off_package = _build_policy_sign_off_package(record=record, payload=payload)
    report = request_policy_sign_off_report_package_with_lotus_report(
        request={
            "report_request_id": report_request_id,
            "proposal": _proposal_summary(record=record, payload=payload),
            "report_type": "PORTFOLIO_REVIEW",
            "requested_by": payload.requested_by,
            "related_policy_evaluation_id": record.evaluation_id,
            "requested_output_formats": list(payload.requested_output_formats),
            "policy_sign_off_package": sign_off_package,
            "reason": payload.reason,
        }
    )
    event = append_policy_evaluation_event(
        evaluation_id=evaluation_id,
        event_type="POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED",
        actor_id=payload.requested_by,
        idempotency_key=idempotency_key,
        reason={
            "policy_report_package_contract_version": _REPORTING_CONTRACT_VERSION,
            "policy_report_package_request_hash": request_hash,
            "report_package_id": report.report_reference_id,
            "report_package_status": _policy_report_status(report.status),
            "source_evaluation_hash": payload.source_evaluation_hash,
            "portfolio_id": payload.portfolio_id,
            "client_ready_publication": _CLIENT_READY_PUBLICATION,
            "requested_output_formats": list(payload.requested_output_formats),
            "report_request_id": report.report_request_id,
            "report_service": report.report_service,
            "report_status": report.status,
            "report_status_url": report.artifact_url,
            "render": deepcopy(report.explanation.get("render", {})),
            "archive": deepcopy(report.explanation.get("archive", {})),
            "policy_sign_off_package": {
                "package_status": sign_off_package["package_status"],
                "evaluation_id": record.evaluation_id,
                "evaluation_hash": record.evaluation_hash,
                "policy_pack_id": record.policy_pack_id,
                "policy_version": record.policy_version,
            },
            "reason": deepcopy(payload.reason),
        },
    )
    return PolicyEvaluationReportPackageResponse(
        evaluation=get_policy_evaluation_record(evaluation_id=evaluation_id),
        report_package_event=event,
        report=report,
        replayed=False,
    )


def _validate_report_request(
    *, record: PolicyEvaluationRecord, payload: PolicyEvaluationReportPackageRequest
) -> None:
    if payload.source_evaluation_hash != record.evaluation_hash:
        raise ProposalValidationError("POLICY_REPORT_PACKAGE_HASH_MISMATCH")
    if payload.client_ready_document_requested:
        raise ProposalValidationError("POLICY_CLIENT_READY_DOCUMENT_NOT_SUPPORTED")
    if not [
        item
        for item in payload.requested_output_formats
        if str(item).strip().lower() in {"pdf", "json"}
    ]:
        raise ProposalValidationError("POLICY_REPORT_PACKAGE_OUTPUT_FORMAT_REQUIRED")

    workflow = get_policy_evaluation_workflow(evaluation_id=record.evaluation_id)
    if workflow.sign_off_status != "SIGNED_OFF":
        raise ProposalValidationError("POLICY_REPORT_PACKAGE_REQUIRES_SIGN_OFF")
    if workflow.sign_off_blockers:
        raise ProposalValidationError("POLICY_REPORT_PACKAGE_REQUIREMENTS_OPEN")


def _find_replayed_report_event(
    *, evaluation_id: str, idempotency_key: str, request_hash: str
) -> PolicyEvaluationAuditEvent | None:
    for event in list_policy_evaluation_events(evaluation_id=evaluation_id):
        if event.idempotency_key != idempotency_key:
            continue
        prior_hash = event.reason_json.get("policy_report_package_request_hash")
        if prior_hash != request_hash:
            raise ProposalIdempotencyConflictError("POLICY_EVALUATION_IDEMPOTENCY_KEY_CONFLICT")
        return event
    return None


def _build_policy_sign_off_package(
    *, record: PolicyEvaluationRecord, payload: PolicyEvaluationReportPackageRequest
) -> dict[str, Any]:
    workflow = get_policy_evaluation_workflow(evaluation_id=record.evaluation_id)
    events = list_policy_evaluation_events(evaluation_id=record.evaluation_id)
    return {
        "package_type": "ADVISORY_POLICY_SIGN_OFF_PACKAGE",
        "package_status": "SIGNED_OFF_SOURCE_PACKAGE",
        "reporting_contract_version": _REPORTING_CONTRACT_VERSION,
        "evaluation": record.model_dump(mode="json"),
        "workflow": workflow.model_dump(mode="json"),
        "audit_events": [event.model_dump(mode="json") for event in events],
        "source_lineage": {
            "policy_content_hash": record.policy_content_hash,
            "source_evidence_hash": record.source_evidence_hash,
            "evaluation_hash": record.evaluation_hash,
            "rule_result_hashes": dict(record.rule_result_hashes),
            "source_refs": list(record.source_refs),
            "source_gaps": list(record.source_gaps),
        },
        "disclosure_requirements": list(record.disclosure_requirements),
        "consent_requirements": list(record.consent_requirements),
        "approval_dependencies": list(record.approval_dependencies),
        "client_ready_publication": _CLIENT_READY_PUBLICATION,
        "requested_output_formats": list(payload.requested_output_formats),
        "reason": deepcopy(payload.reason),
    }


def _proposal_summary(
    *, record: PolicyEvaluationRecord, payload: PolicyEvaluationReportPackageRequest
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    selectors = _as_mapping(
        _as_mapping(record.evaluation_json.get("applicability")).get("matched_selectors")
    )
    return {
        "proposal_id": record.proposal_id,
        "portfolio_id": payload.portfolio_id,
        "mandate_id": selectors.get("mandate_id"),
        "jurisdiction": selectors.get("jurisdiction"),
        "created_by": record.created_by,
        "created_at": record.generated_at,
        "last_event_at": now,
        "current_state": "EXECUTION_READY",
        "current_version_no": 1,
        "title": "Policy sign-off package",
        "lifecycle_origin": "WORKSPACE_HANDOFF",
        "source_workspace_id": None,
    }


def _report_response_from_event(
    *, record: PolicyEvaluationRecord, event: PolicyEvaluationAuditEvent
) -> ProposalReportResponse:
    reason = event.reason_json
    return ProposalReportResponse(
        proposal=_proposal_summary(
            record=record,
            payload=PolicyEvaluationReportPackageRequest(
                requested_by=event.actor_id,
                portfolio_id=str(reason.get("portfolio_id") or "UNKNOWN_PORTFOLIO"),
                source_evaluation_hash=record.evaluation_hash,
                requested_output_formats=[
                    str(item) for item in reason.get("requested_output_formats", ["pdf"])
                ],
            ),
        ),
        report_request_id=str(reason.get("report_request_id") or event.event_id),
        report_type=cast(ProposalReportType, "PORTFOLIO_REVIEW"),
        report_service=str(reason.get("report_service") or "lotus-report"),
        status=str(reason.get("report_status") or "ACCEPTED"),
        generated_at=event.occurred_at,
        report_reference_id=str(reason.get("report_package_id") or event.event_id),
        artifact_url=reason.get("report_status_url"),
        explanation={
            "ownership": "REPORT_RENDER_ARCHIVE_OWNED_BY_LOTUS_REPORT_RENDER_ARCHIVE",
            "policy_sign_off_package": reason.get("policy_sign_off_package", {}),
            "render": reason.get("render", {}),
            "archive": reason.get("archive", {}),
            "client_ready_publication": _CLIENT_READY_PUBLICATION,
        },
    )


def _request_hash(
    *, record: PolicyEvaluationRecord, payload: PolicyEvaluationReportPackageRequest
) -> str:
    return str(
        hash_canonical_payload(
            {
                "operation": "POLICY_REPORT_PACKAGE_REQUESTED",
                "evaluation_id": record.evaluation_id,
                "source_evaluation_hash": payload.source_evaluation_hash,
                "requested_by": payload.requested_by,
                "portfolio_id": payload.portfolio_id,
                "requested_output_formats": list(payload.requested_output_formats),
                "client_ready_document_requested": payload.client_ready_document_requested,
                "reason": payload.reason,
            }
        )
    )


def _policy_report_status(report_status: str) -> str:
    if report_status == "ARCHIVED":
        return "ARCHIVED"
    if report_status in {"READY", "ACCEPTED"}:
        return "RECORDED"
    return report_status


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
