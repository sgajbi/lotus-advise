"""Tactical house-view affected-cohort source product."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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


def _eligible_portfolio_types(request: TacticalHouseViewCohortRequest) -> set[str]:
    return {normalize_portfolio_type(value) for value in request.eligible_portfolio_types}


def _affected_portfolio(
    candidate: TacticalHouseViewCandidatePortfolio,
) -> TacticalHouseViewAffectedPortfolio:
    return TacticalHouseViewAffectedPortfolio(
        portfolio_id=candidate.portfolio_id,
        mandate_id=candidate.mandate_id,
        inclusion_reason_codes=candidate_inclusion_reason_codes(candidate),
        source_refs=candidate.source_refs,
    )


def _excluded_portfolio(
    candidate: TacticalHouseViewCandidatePortfolio,
    exclusion_reason_codes: list[str],
) -> TacticalHouseViewExcludedPortfolio:
    return TacticalHouseViewExcludedPortfolio(
        portfolio_id=candidate.portfolio_id,
        exclusion_reason_codes=exclusion_reason_codes,
        source_refs=candidate.source_refs,
    )


def _classify_candidate(
    candidate: TacticalHouseViewCandidatePortfolio,
    *,
    eligible_types: set[str],
    min_exposure_weight: Decimal | None,
) -> tuple[TacticalHouseViewAffectedPortfolio | None, TacticalHouseViewExcludedPortfolio | None]:
    exclusion_reasons = candidate_exclusion_reasons(
        candidate=candidate,
        eligible_types=eligible_types,
        min_exposure_weight=min_exposure_weight,
    )
    if exclusion_reasons:
        return None, _excluded_portfolio(candidate, exclusion_reasons)
    return _affected_portfolio(candidate), None


def _classify_candidates(
    request: TacticalHouseViewCohortRequest,
) -> tuple[list[TacticalHouseViewAffectedPortfolio], list[TacticalHouseViewExcludedPortfolio]]:
    affected: list[TacticalHouseViewAffectedPortfolio] = []
    excluded: list[TacticalHouseViewExcludedPortfolio] = []
    eligible_types = _eligible_portfolio_types(request)

    for candidate in request.candidate_portfolios:
        affected_portfolio, excluded_portfolio = _classify_candidate(
            candidate,
            eligible_types=eligible_types,
            min_exposure_weight=request.min_exposure_weight,
        )
        if affected_portfolio is not None:
            affected.append(affected_portfolio)
        if excluded_portfolio is not None:
            excluded.append(excluded_portfolio)

    return affected, excluded


def _cohort_source_refs(
    request: TacticalHouseViewCohortRequest,
) -> list[TacticalHouseViewSourceRef]:
    return dedupe_source_refs(
        [*request.tactical_view.source_refs]
        + [ref for candidate in request.candidate_portfolios for ref in candidate.source_refs]
    )


def _finalize_cohort_identity(
    cohort: TacticalHouseViewAffectedCohort,
) -> TacticalHouseViewAffectedCohort:
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


def build_tactical_house_view_affected_cohort(
    request: TacticalHouseViewCohortRequest,
    *,
    generated_at: datetime | None = None,
) -> TacticalHouseViewAffectedCohort:
    """Build a deterministic tactical house-view cohort without source-fact recalculation."""

    generated_at = generated_at or datetime.now(timezone.utc)
    affected, excluded = _classify_candidates(request)

    cohort_supportability = supportability(
        evaluated_candidate_count=len(request.candidate_portfolios),
        affected_count=len(affected),
        excluded_count=len(excluded),
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
        source_refs=_cohort_source_refs(request),
        content_hash="",
        generated_at=generated_at.isoformat(),
        correlation_id=request.correlation_id,
    )
    return _finalize_cohort_identity(cohort)


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
    cohorts = _stored_cohorts_by_recency()
    if portfolio_id is not None:
        cohorts = [cohort for cohort in cohorts if _cohort_contains_portfolio(cohort, portfolio_id)]
    return [cohort.model_copy(deep=True) for cohort in cohorts[:limit]]


def _stored_cohorts_by_recency() -> list[TacticalHouseViewAffectedCohort]:
    return sorted(
        _COHORT_STORE.values(),
        key=lambda item: (item.generated_at, item.cohort_id),
        reverse=True,
    )


def _cohort_contains_portfolio(
    cohort: TacticalHouseViewAffectedCohort,
    portfolio_id: str,
) -> bool:
    return any(affected.portfolio_id == portfolio_id for affected in cohort.affected_portfolios)


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
