"""API routes for tactical house-view source cohorts."""

from fastapi import APIRouter, status

from src.core.tactical_house_view import (
    TacticalHouseViewAffectedCohort,
    TacticalHouseViewCohortRequest,
    build_tactical_house_view_affected_cohort,
    record_tactical_house_view_affected_cohort,
)

router = APIRouter(prefix="/advisory/tactical-house-view", tags=["Tactical House View"])


@router.post(
    "/cohorts/evaluate",
    response_model=TacticalHouseViewAffectedCohort,
    status_code=status.HTTP_200_OK,
    summary="Evaluate tactical house-view affected cohort",
    description=(
        "What: Build the governed lotus-advise TacticalHouseViewAffectedCohort:v1 source product "
        "from a bank-authored tactical house-view instruction and source-backed candidate "
        "portfolios.\\n"
        "When: Use when downstream discretionary portfolio-management workflows need an "
        "Advise-owned tactical house-view cohort without recomputing advisory, core, or risk "
        "facts in Manage.\\n"
        "How: The endpoint filters only source-backed discretionary/managed candidate portfolios, "
        "preserves house-view and candidate source refs, returns included and excluded portfolios, "
        "and emits deterministic cohort and content hashes. It does not discover the global "
        "portfolio universe, create rebalance waves, approve trades, or claim OMS execution."
    ),
)
def evaluate_tactical_house_view_cohort(
    request: TacticalHouseViewCohortRequest,
) -> TacticalHouseViewAffectedCohort:
    return record_tactical_house_view_affected_cohort(
        build_tactical_house_view_affected_cohort(request)
    )
