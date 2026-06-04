from src.core.advisor_cockpit.action_sources import HouseViewImpactActionSource
from src.core.advisor_cockpit.reference_models import CockpitCallerContext
from src.core.advisor_cockpit.repository import AdvisorCockpitRepository
from src.core.advisor_cockpit.source_read_model import (
    AdvisorCockpitSourceBatch,
    AdvisorCockpitSourceReadModel,
    build_advisor_cockpit_source_read_model,
)
from src.core.policy_packs.persistence import list_policy_evaluation_records
from src.core.tactical_house_view import (
    TacticalHouseViewAffectedCohort,
    list_tactical_house_view_affected_cohorts,
)


def load_advisor_cockpit_source_read_model(
    *,
    repository: AdvisorCockpitRepository,
    caller_context: CockpitCallerContext,
    portfolio_id: str | None,
    correlation_id: str | None,
    source_limit: int,
) -> AdvisorCockpitSourceReadModel:
    proposals, _next_cursor = repository.list_proposals(
        portfolio_id=portfolio_id,
        state=None,
        created_by=None if portfolio_id is not None else caller_context.advisor_id,
        created_from=None,
        created_to=None,
        limit=source_limit,
        cursor=None,
    )
    proposal_ids = [proposal.proposal_id for proposal in proposals]
    return build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=proposals,
            policy_evaluations=list_policy_evaluation_records(
                evaluation_status=None,
                portfolio_id=portfolio_id,
            )[:source_limit],
            memos=repository.list_memos_for_proposals(proposal_ids=proposal_ids)[:source_limit],
            approvals=repository.list_approvals_for_proposals(proposal_ids=proposal_ids)[
                :source_limit
            ],
            workflow_events=repository.list_events_for_proposals(proposal_ids=proposal_ids)[
                :source_limit
            ],
            house_view_impacts=_house_view_impacts(
                list_tactical_house_view_affected_cohorts(
                    portfolio_id=portfolio_id,
                    limit=source_limit,
                ),
                portfolio_id=portfolio_id,
                correlation_id=correlation_id,
            ),
        )
    )


def _house_view_impacts(
    cohorts: list[TacticalHouseViewAffectedCohort],
    *,
    portfolio_id: str | None,
    correlation_id: str | None,
) -> list[HouseViewImpactActionSource]:
    impacts: list[HouseViewImpactActionSource] = []
    for cohort in cohorts:
        for affected in cohort.affected_portfolios:
            if portfolio_id is not None and affected.portfolio_id != portfolio_id:
                continue
            inclusion_reason_codes = affected.inclusion_reason_codes or [
                "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED"
            ]
            impact_code = (
                "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED"
                if "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED" in inclusion_reason_codes
                else inclusion_reason_codes[0]
            )
            impacts.append(
                HouseViewImpactActionSource(
                    cohort_id=cohort.cohort_id,
                    tactical_view_id=cohort.tactical_view_id,
                    tactical_view_version=cohort.tactical_view_version,
                    portfolio_id=affected.portfolio_id,
                    impact_code=impact_code,
                    summary=(
                        "Portfolio is included in a source-backed tactical house-view affected "
                        "cohort for discretionary portfolio-management review."
                    ),
                    lineage_id=f"tactical_house_view_cohort:{cohort.cohort_id}",
                    content_hash=cohort.content_hash,
                    source_timestamp=cohort.generated_at,
                    materiality_rank=52,
                    correlation_id=correlation_id or cohort.correlation_id,
                )
            )
    return impacts
