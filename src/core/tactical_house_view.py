"""Tactical house-view affected-cohort source product."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.tactical_house_view_models import (
    TacticalHouseViewAction as TacticalHouseViewAction,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewAffectedCohort as TacticalHouseViewAffectedCohort,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewAffectedPortfolio as TacticalHouseViewAffectedPortfolio,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewAlignment as TacticalHouseViewAlignment,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewCandidatePortfolio as TacticalHouseViewCandidatePortfolio,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewCohortRequest as TacticalHouseViewCohortRequest,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewDefinition as TacticalHouseViewDefinition,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewExcludedPortfolio as TacticalHouseViewExcludedPortfolio,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewSourceRef as TacticalHouseViewSourceRef,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewSupportability as TacticalHouseViewSupportability,
)
from src.core.tactical_house_view_models import (
    TacticalHouseViewSupportabilityState as TacticalHouseViewSupportabilityState,
)
from src.core.tactical_house_view_rules import (
    candidate_exclusion_reasons,
    candidate_inclusion_reason_codes,
    dedupe_source_refs,
    normalize_portfolio_type,
    supportability,
)

_COHORT_STORE: dict[str, TacticalHouseViewAffectedCohort] = {}


def build_tactical_house_view_affected_cohort(
    request: TacticalHouseViewCohortRequest,
    *,
    generated_at: datetime | None = None,
) -> TacticalHouseViewAffectedCohort:
    """Build a deterministic tactical house-view cohort without source-fact recalculation."""

    generated_at = generated_at or datetime.now(timezone.utc)
    eligible_types = {normalize_portfolio_type(value) for value in request.eligible_portfolio_types}
    affected: list[TacticalHouseViewAffectedPortfolio] = []
    excluded: list[TacticalHouseViewExcludedPortfolio] = []

    for candidate in request.candidate_portfolios:
        exclusion_reasons = candidate_exclusion_reasons(
            candidate=candidate,
            eligible_types=eligible_types,
            min_exposure_weight=request.min_exposure_weight,
        )
        if exclusion_reasons:
            excluded.append(
                TacticalHouseViewExcludedPortfolio(
                    portfolio_id=candidate.portfolio_id,
                    exclusion_reason_codes=exclusion_reasons,
                    source_refs=candidate.source_refs,
                )
            )
            continue
        affected.append(
            TacticalHouseViewAffectedPortfolio(
                portfolio_id=candidate.portfolio_id,
                mandate_id=candidate.mandate_id,
                inclusion_reason_codes=candidate_inclusion_reason_codes(candidate),
                source_refs=candidate.source_refs,
            )
        )

    cohort_supportability = supportability(
        evaluated_candidate_count=len(request.candidate_portfolios),
        affected_count=len(affected),
        excluded_count=len(excluded),
    )
    source_refs = dedupe_source_refs(
        [*request.tactical_view.source_refs]
        + [ref for candidate in request.candidate_portfolios for ref in candidate.source_refs]
    )
    cohort = TacticalHouseViewAffectedCohort(
        cohort_id="",
        tactical_view_id=request.tactical_view.tactical_view_id,
        tactical_view_version=request.tactical_view.tactical_view_version,
        theme_id=request.tactical_view.theme_id,
        as_of_date=request.tactical_view.as_of_date,
        target_action=request.tactical_view.target_action,
        affected_portfolios=sorted(affected, key=lambda item: item.portfolio_id),
        excluded_portfolios=sorted(excluded, key=lambda item: item.portfolio_id),
        supportability=cohort_supportability,
        source_refs=source_refs,
        content_hash="",
        generated_at=generated_at.isoformat(),
        correlation_id=request.correlation_id,
    )
    payload = cohort.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    payload["cohort_id"] = hash_canonical_payload(
        strip_keys(payload, exclude={"cohort_id", "content_hash", "generated_at"})
    )
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return cast(
        TacticalHouseViewAffectedCohort,
        TacticalHouseViewAffectedCohort.model_validate(payload),
    )


def record_tactical_house_view_affected_cohort(
    cohort: TacticalHouseViewAffectedCohort,
) -> TacticalHouseViewAffectedCohort:
    _COHORT_STORE[cohort.cohort_id] = cohort.model_copy(deep=True)
    return cohort


def list_tactical_house_view_affected_cohorts(
    *,
    portfolio_id: str | None,
    limit: int,
) -> list[TacticalHouseViewAffectedCohort]:
    cohorts = sorted(
        _COHORT_STORE.values(),
        key=lambda item: (item.generated_at, item.cohort_id),
        reverse=True,
    )
    if portfolio_id is not None:
        cohorts = [
            cohort
            for cohort in cohorts
            if any(affected.portfolio_id == portfolio_id for affected in cohort.affected_portfolios)
        ]
    return [cohort.model_copy(deep=True) for cohort in cohorts[:limit]]


def clear_tactical_house_view_affected_cohorts_for_tests() -> None:
    _COHORT_STORE.clear()


__all__ = [
    "TacticalHouseViewAction",
    "TacticalHouseViewAffectedCohort",
    "TacticalHouseViewAffectedPortfolio",
    "TacticalHouseViewAlignment",
    "TacticalHouseViewCandidatePortfolio",
    "TacticalHouseViewCohortRequest",
    "TacticalHouseViewDefinition",
    "TacticalHouseViewExcludedPortfolio",
    "TacticalHouseViewSourceRef",
    "TacticalHouseViewSupportability",
    "TacticalHouseViewSupportabilityState",
    "build_tactical_house_view_affected_cohort",
    "clear_tactical_house_view_affected_cohorts_for_tests",
    "list_tactical_house_view_affected_cohorts",
    "record_tactical_house_view_affected_cohort",
]
