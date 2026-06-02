from typing import Any

from src.core.proposals.models import (
    ProposalMemoAuditEvent,
    ProposalMemoResponse,
    ProposalRecord,
    ProposalReportResponse,
)
from src.core.proposals.persistence_models import (
    ProposalMemoEventRecord,
    ProposalMemoRecord,
)
from src.core.proposals.projections import to_proposal_summary
from src.core.proposals.repository import ProposalRepository


def build_memo_response(
    *,
    repository: ProposalRepository,
    proposal: ProposalRecord,
    memo: ProposalMemoRecord,
) -> ProposalMemoResponse:
    events = repository.list_memo_events(memo_id=memo.memo_id)
    projection = dict(memo.projection_json)
    projection.setdefault("client_ready_publication", "BLOCKED")
    return ProposalMemoResponse(
        proposal=to_proposal_summary(proposal),
        proposal_version_no=memo.proposal_version_no,
        proposal_version_id=memo.proposal_version_id,
        memo_id=memo.memo_id,
        artifact_id=memo.artifact_id,
        memo_version=memo.memo_version,
        memo_status=memo.memo_status,
        lifecycle_status=memo.lifecycle_status,
        created_by=memo.created_by,
        created_at=memo.created_at.isoformat(),
        source_input_hash=memo.source_input_hash,
        memo_hash=memo.memo_hash,
        memo=dict(memo.memo_json),
        projection=projection,
        review_posture=latest_event_posture(events, event_type="MEMO_REVIEW_RECORDED"),
        report_package_posture=latest_event_posture(
            events, event_type="MEMO_REPORT_PACKAGE_RECORDED"
        ),
        ai_commentary_posture=latest_event_posture(events, event_type="MEMO_AI_REFERENCE_RECORDED"),
        replay_metadata=dict(memo.replay_metadata_json),
        audit_events=[to_audit_event(event) for event in events],
        event_count=len(events),
        replay_evidence_path=(
            f"/advisory/proposals/{memo.proposal_id}/versions/"
            f"{memo.proposal_version_no}/memo/replay-evidence"
        ),
        lineage_path=f"/advisory/proposals/{memo.proposal_id}/memos/lineage",
        read_posture={
            "source": "PERSISTED_MEMO_RECORD",
            "memo_api_supported": True,
            "report_package_generation_supported": True,
            "report_render_archive_supported": True,
            "ai_commentary_supported": True,
            "gateway_supported": False,
            "workbench_supported": False,
            "client_ready_publication": projection["client_ready_publication"],
        },
    )


def to_audit_event(event: ProposalMemoEventRecord) -> ProposalMemoAuditEvent:
    return ProposalMemoAuditEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        actor_id=event.actor_id,
        occurred_at=event.occurred_at.isoformat(),
        reason=dict(event.reason_json),
    )


def latest_event_posture(
    events: list[ProposalMemoEventRecord],
    *,
    event_type: str,
) -> dict[str, Any]:
    matching = [event for event in events if event.event_type == event_type]
    if not matching:
        return {"status": "NOT_RECORDED"}
    latest = matching[-1]
    return {
        "status": "RECORDED",
        "event_id": latest.event_id,
        "actor_id": latest.actor_id,
        "occurred_at": latest.occurred_at.isoformat(),
        **dict(latest.reason_json),
    }


def memo_report_status(report_status: str) -> str:
    if report_status in {"READY", "ARCHIVED", "COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        return "RECORDED"
    if report_status in {"FAILED", "CANCELLED"}:
        return "BLOCKED"
    return "DEGRADED"


def report_response_from_event(
    *,
    proposal: ProposalRecord,
    event: ProposalMemoEventRecord,
) -> ProposalReportResponse:
    reason = dict(event.reason_json)
    return ProposalReportResponse(
        proposal=to_proposal_summary(proposal),
        report_request_id=str(reason.get("report_request_id") or event.event_id),
        report_type="PORTFOLIO_REVIEW",
        report_service=str(reason.get("report_service") or "lotus-report"),
        status=str(reason.get("report_status") or "ACCEPTED"),
        generated_at=event.occurred_at.isoformat(),
        report_reference_id=str(reason.get("report_package_id") or event.event_id),
        artifact_url=reason.get("report_status_url"),
        explanation={
            "ownership": "REPORT_RENDER_ARCHIVE_OWNED_BY_LOTUS_REPORT_RENDER_ARCHIVE",
            "render": reason.get("render", {}),
            "archive": reason.get("archive", {}),
            "client_ready_publication": reason.get("client_ready_publication", "BLOCKED"),
            "replayed_from_memo_event": event.event_id,
        },
    )


def commentary_from_ai_event(event: ProposalMemoEventRecord) -> dict[str, Any]:
    reason = dict(event.reason_json)
    return {
        "status": reason.get("ai_status", "UNAVAILABLE"),
        "sections": reason.get("sections", []),
        "lineage": reason.get("lineage", {}),
        "review_guidance": reason.get("review_guidance", []),
        "client_ready_publication": reason.get("client_ready_publication", "BLOCKED"),
        "review_required": reason.get("review_required", True),
        "authoritative_for_memo_status": reason.get("authoritative_for_memo_status", False),
    }


def archive_refs_from_report_posture(report_posture: dict[str, Any]) -> list[dict[str, Any]]:
    archive = report_posture.get("archive")
    if not isinstance(archive, dict) or not archive:
        return []
    refs: dict[str, Any] = {
        "archive_request_id": archive.get("archive_request_id"),
        "document_id": archive.get("document_id"),
        "completed_at": archive.get("completed_at"),
        "retention_posture": archive.get("retention_posture", "OWNED_BY_LOTUS_ARCHIVE"),
        "legal_hold_posture": archive.get("legal_hold_posture", "OWNED_BY_LOTUS_ARCHIVE"),
        "access_audit_ref": archive.get("access_audit_ref"),
    }
    return [{key: value for key, value in refs.items() if value is not None}]


def project_sections(memo_json: dict[str, Any], *, audience: str | None) -> list[dict[str, Any]]:
    sections = memo_json.get("sections")
    if not isinstance(sections, list):
        return []
    projected = [section for section in sections if isinstance(section, dict)]
    if audience is None:
        return projected
    return [section for section in projected if audience in section.get("audience_visibility", [])]


def memo_has_replay_metadata(memo: ProposalMemoRecord) -> bool:
    required = {
        "proposal_request_hash",
        "proposal_artifact_hash",
        "proposal_simulation_hash",
        "memo_source_input_hash",
        "memo_request_hash",
        "replay_policy",
    }
    return required.issubset(set(memo.replay_metadata_json))
