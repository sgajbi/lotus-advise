from __future__ import annotations

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_sources import (
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    MemoPackageBlockedActionSource,
    ReportRenderArchiveActionSource,
)
from src.core.advisor_cockpit.models import AdvisoryActionItem


def build_memo_package_blocked_action(
    source: MemoPackageBlockedActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.memo_id,
            action_family="MEMO_PACKAGE_BLOCKED",
            status="BLOCKED",
            priority="HIGH",
            owner_role=source.owner_role,
            title="Memo package blocked",
            next_required_action="Resolve the memo evidence gap before advisor-use packaging.",
            reason_codes=[source.blockage_code, "CLIENT_READY_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                memo_id=source.memo_id,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                action_components.evidence_ref(
                    evidence_id=source.memo_id,
                    evidence_type="PROPOSAL_MEMO",
                    summary=source.summary,
                    access_class="RESTRICTED_CUSTOMER_EVIDENCE",
                )
            ],
            source_readiness_gaps=[
                action_components.source_readiness_gap(
                    source_family="proposal_memo",
                    gap_code=source.blockage_code,
                    owner_role=source.owner_role,
                    message="Memo source evidence must be resolved before packaging continues.",
                )
            ],
            lineage_refs=action_components.lineage_refs(source.lineage_id, source.content_hash),
            unsupported_capabilities=["CLIENT_READY_PUBLICATION"],
            correlation_id=source.correlation_id,
        )
    )


def build_report_render_archive_action(
    source: ReportRenderArchiveActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.readiness_id,
            action_family="REPORT_RENDER_ARCHIVE_BLOCKED",
            status="BLOCKED",
            priority="HIGH",
            owner_role=source.owner_role,
            title="Report and archive readiness blocked",
            next_required_action=(
                "Resolve report/render/archive readiness before presenting completed packaging."
            ),
            reason_codes=[source.readiness_code, "CLIENT_READY_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                memo_id=source.memo_id,
                report_ref=source.readiness_id,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                action_components.evidence_ref(
                    evidence_id=source.readiness_id,
                    evidence_type="REPORT_RENDER_ARCHIVE_READINESS",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            source_readiness_gaps=[
                action_components.source_readiness_gap(
                    source_family="report_render_archive",
                    gap_code=source.readiness_code,
                    owner_role=source.owner_role,
                    message=source.summary,
                )
            ],
            lineage_refs=action_components.lineage_refs(source.lineage_id, source.content_hash),
            unsupported_capabilities=["CLIENT_READY_PUBLICATION"],
            correlation_id=source.correlation_id,
        )
    )
