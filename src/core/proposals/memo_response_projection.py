from typing import Any

from src.core.proposals.memo_persistence_models import (
    ProposalMemoEventRecord,
    ProposalMemoRecord,
)
from src.core.proposals.models import (
    ProposalMemoAuditEvent,
    ProposalMemoLineageItem,
    ProposalMemoLineageResponse,
    ProposalMemoProjectionResponse,
    ProposalMemoReplayEvidenceResponse,
    ProposalMemoResponse,
    ProposalRecord,
    ProposalReportResponse,
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


def build_memo_projection_response(
    *,
    memo_response: ProposalMemoResponse,
    audience: str | None,
) -> ProposalMemoProjectionResponse:
    sections = project_sections(memo_response.memo, audience=audience)
    return ProposalMemoProjectionResponse(
        proposal=memo_response.proposal,
        proposal_version_no=memo_response.proposal_version_no,
        memo_id=memo_response.memo_id,
        memo_hash=memo_response.memo_hash,
        audience=audience,
        projection=memo_response.projection,
        sections=sections,
        projection_posture={
            "source": "PERSISTED_MEMO_RECORD",
            "mutation_performed": False,
            "audience_filter": audience,
            "client_ready_publication": memo_response.projection.get(
                "client_ready_publication", "BLOCKED"
            ),
            "gateway_supported": False,
            "workbench_supported": False,
        },
    )


def build_memo_lineage_response(
    *,
    repository: ProposalRepository,
    proposal: ProposalRecord,
    memos: list[ProposalMemoRecord],
) -> ProposalMemoLineageResponse:
    items = []
    for memo in memos:
        events = repository.list_memo_events(memo_id=memo.memo_id)
        report_posture = latest_event_posture(events, event_type="MEMO_REPORT_PACKAGE_RECORDED")
        ai_posture = latest_event_posture(events, event_type="MEMO_AI_REFERENCE_RECORDED")
        items.append(
            ProposalMemoLineageItem(
                memo_id=memo.memo_id,
                proposal_version_no=memo.proposal_version_no,
                proposal_version_id=memo.proposal_version_id,
                memo_status=memo.memo_status,
                lifecycle_status=memo.lifecycle_status,
                memo_hash=memo.memo_hash,
                source_input_hash=memo.source_input_hash,
                created_at=memo.created_at.isoformat(),
                event_count=len(events),
                report_package_posture=report_posture,
                archive_refs=archive_refs_from_report_posture(report_posture),
                ai_commentary_posture=ai_posture,
            )
        )
    return ProposalMemoLineageResponse(
        proposal=to_proposal_summary(proposal),
        memo_count=len(items),
        latest_memo_id=items[-1].memo_id if items else None,
        lineage_complete=all(memo_has_replay_metadata(memo) for memo in memos),
        memos=items,
        lineage_posture={
            "source": "PERSISTED_MEMO_RECORDS",
            "memo_api_supported": True,
            "gateway_supported": False,
            "workbench_supported": False,
            "client_ready_publication": "BLOCKED",
        },
    )


def build_memo_replay_evidence_response(
    *,
    proposal_id: str,
    version_no: int,
    memo_response: ProposalMemoResponse,
) -> ProposalMemoReplayEvidenceResponse:
    replay_metadata = memo_response.replay_metadata
    return ProposalMemoReplayEvidenceResponse(
        subject={
            "proposal_id": proposal_id,
            "proposal_version_no": version_no,
            "proposal_version_id": memo_response.proposal_version_id,
            "memo_id": memo_response.memo_id,
        },
        hashes={
            "memo_hash": memo_response.memo_hash,
            "source_input_hash": memo_response.source_input_hash,
            "proposal_request_hash": replay_metadata.get("proposal_request_hash"),
            "proposal_artifact_hash": replay_metadata.get("proposal_artifact_hash"),
            "proposal_simulation_hash": replay_metadata.get("proposal_simulation_hash"),
            "memo_request_hash": replay_metadata.get("memo_request_hash"),
        },
        replay_metadata=replay_metadata,
        audit_events=memo_response.audit_events,
        evidence={
            "memo_status": memo_response.memo_status,
            "lifecycle_status": memo_response.lifecycle_status,
            "projection": memo_response.projection,
            "review_posture": memo_response.review_posture,
            "report_package_posture": memo_response.report_package_posture,
            "ai_commentary_posture": memo_response.ai_commentary_posture,
        },
        explanation={
            "source": "PERSISTED_MEMO_RECORD",
            "replay_policy": replay_metadata.get("replay_policy", "EXACT_SOURCE_HASH_MATCH"),
            "mutation_performed": False,
            "client_ready_publication": "BLOCKED",
            "gateway_supported": False,
            "workbench_supported": False,
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
    return [
        section
        for section in _memo_section_dicts(sections)
        if _section_visible_to_audience(section=section, audience=audience)
    ]


def _memo_section_dicts(sections: list[Any]) -> list[dict[str, Any]]:
    return [section for section in sections if isinstance(section, dict)]


def _section_visible_to_audience(*, section: dict[str, Any], audience: str | None) -> bool:
    if audience is None:
        return True
    visibility = section.get("audience_visibility")
    return isinstance(visibility, list) and audience in visibility


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
