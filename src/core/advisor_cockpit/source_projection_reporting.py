from src.core.advisor_cockpit.action_sources import ReportRenderArchiveActionSource
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord


def build_report_render_archive_sources(
    *,
    records: list[ProposalMemoRecord],
    proposals: dict[str, ProposalRecord],
) -> list[ReportRenderArchiveActionSource]:
    return [
        source
        for record in records
        if (
            source := _report_readiness_source(
                record,
                proposal=proposals.get(record.proposal_id),
            )
        )
        is not None
    ]


def _report_readiness_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
) -> ReportRenderArchiveActionSource | None:
    if record.memo_status != "READY":
        return None
    if not record.report_package_events_json:
        return _report_package_readiness_source(record, proposal=proposal)
    if not record.archive_refs_json:
        return _archive_ref_readiness_source(record, proposal=proposal)
    return None


def _report_package_readiness_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
) -> ReportRenderArchiveActionSource:
    return _report_readiness_action_source(
        record,
        proposal=proposal,
        readiness_suffix="report_package",
        readiness_code="REPORT_PACKAGE_NOT_REQUESTED",
        summary=(
            "Advisor-use memo is ready, but report/render/archive package evidence is not recorded."
        ),
        owner_role="REPORTING_OWNER",
        materiality_rank=58,
    )


def _archive_ref_readiness_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
) -> ReportRenderArchiveActionSource:
    return _report_readiness_action_source(
        record,
        proposal=proposal,
        readiness_suffix="archive_ref",
        readiness_code="ARCHIVE_REF_MISSING",
        summary="Report package event exists, but archive reference evidence is not recorded.",
        owner_role="ARCHIVE_OWNER",
        materiality_rank=54,
    )


def _report_readiness_action_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
    readiness_suffix: str,
    readiness_code: str,
    summary: str,
    owner_role: str,
    materiality_rank: int,
) -> ReportRenderArchiveActionSource:
    return ReportRenderArchiveActionSource(
        readiness_id=f"report_archive_readiness_{record.memo_id}_{readiness_suffix}",
        memo_id=record.memo_id,
        proposal_id=record.proposal_id,
        portfolio_id=proposal.portfolio_id if proposal is not None else None,
        readiness_code=readiness_code,
        summary=summary,
        owner_role=owner_role,
        source_timestamp=record.created_at.isoformat(),
        materiality_rank=materiality_rank,
        lineage_id=f"proposal_memo:{record.memo_id}",
        content_hash=record.memo_hash,
    )


__all__ = ["build_report_render_archive_sources"]
