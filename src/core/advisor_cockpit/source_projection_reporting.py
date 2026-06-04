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
        return ReportRenderArchiveActionSource(
            readiness_id=f"report_archive_readiness_{record.memo_id}_report_package",
            memo_id=record.memo_id,
            proposal_id=record.proposal_id,
            portfolio_id=proposal.portfolio_id if proposal is not None else None,
            readiness_code="REPORT_PACKAGE_NOT_REQUESTED",
            summary=(
                "Advisor-use memo is ready, but report/render/archive package evidence is not "
                "recorded."
            ),
            owner_role="REPORTING_OWNER",
            source_timestamp=record.created_at.isoformat(),
            materiality_rank=58,
            lineage_id=f"proposal_memo:{record.memo_id}",
            content_hash=record.memo_hash,
        )
    if not record.archive_refs_json:
        return ReportRenderArchiveActionSource(
            readiness_id=f"report_archive_readiness_{record.memo_id}_archive_ref",
            memo_id=record.memo_id,
            proposal_id=record.proposal_id,
            portfolio_id=proposal.portfolio_id if proposal is not None else None,
            readiness_code="ARCHIVE_REF_MISSING",
            summary="Report package event exists, but archive reference evidence is not recorded.",
            owner_role="ARCHIVE_OWNER",
            source_timestamp=record.created_at.isoformat(),
            materiality_rank=54,
            lineage_id=f"proposal_memo:{record.memo_id}",
            content_hash=record.memo_hash,
        )
    return None


__all__ = ["build_report_render_archive_sources"]
