from decimal import Decimal

from src.core.tactical_house_view_models import (
    TacticalHouseViewCandidatePortfolio,
    TacticalHouseViewSourceRef,
    TacticalHouseViewSupportability,
)

PORTFOLIO_TYPE_ALIASES = {
    "DPM": "DISCRETIONARY",
}


def candidate_exclusion_reasons(
    *,
    candidate: TacticalHouseViewCandidatePortfolio,
    eligible_types: set[str],
    min_exposure_weight: Decimal | None,
) -> list[str]:
    reasons: list[str] = []
    if normalize_portfolio_type(candidate.portfolio_type) not in eligible_types:
        reasons.append("TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPE_NOT_ELIGIBLE")
    if not candidate.discretionary_mandate:
        reasons.append("TACTICAL_HOUSE_VIEW_NON_DISCRETIONARY_MANDATE")
    if candidate.alignment_signal == "ALIGNED":
        reasons.append("TACTICAL_HOUSE_VIEW_ALREADY_ALIGNED")
    if candidate.alignment_signal == "UNKNOWN":
        reasons.append("TACTICAL_HOUSE_VIEW_ALIGNMENT_UNKNOWN")
    reasons.extend(
        exposure_exclusion_reasons(
            current_exposure_weight=candidate.current_exposure_weight,
            min_exposure_weight=min_exposure_weight,
        )
    )
    return reasons


def exposure_exclusion_reasons(
    *,
    current_exposure_weight: Decimal | None,
    min_exposure_weight: Decimal | None,
) -> list[str]:
    if min_exposure_weight is None:
        return []
    if current_exposure_weight is None:
        return ["TACTICAL_HOUSE_VIEW_EXPOSURE_EVIDENCE_MISSING"]
    if current_exposure_weight < min_exposure_weight:
        return ["TACTICAL_HOUSE_VIEW_EXPOSURE_BELOW_MINIMUM"]
    return []


def candidate_inclusion_reason_codes(
    candidate: TacticalHouseViewCandidatePortfolio,
) -> list[str]:
    reasons = {
        "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
        f"TACTICAL_HOUSE_VIEW_{candidate.alignment_signal}",
        *candidate.reason_codes,
    }
    return sorted(reasons)


def normalize_portfolio_type(portfolio_type: str) -> str:
    normalized = portfolio_type.strip().upper()
    return PORTFOLIO_TYPE_ALIASES.get(normalized, normalized)


def supportability(
    *,
    evaluated_candidate_count: int,
    affected_count: int,
    excluded_count: int,
) -> TacticalHouseViewSupportability:
    if affected_count == 0:
        return TacticalHouseViewSupportability(
            state="EMPTY",
            reason_codes=["TACTICAL_HOUSE_VIEW_NO_ELIGIBLE_AFFECTED_PORTFOLIOS"],
            evaluated_candidate_count=evaluated_candidate_count,
            affected_count=affected_count,
            excluded_count=excluded_count,
        )
    return TacticalHouseViewSupportability(
        state="READY",
        reason_codes=["TACTICAL_HOUSE_VIEW_AFFECTED_COHORT_READY"],
        evaluated_candidate_count=evaluated_candidate_count,
        affected_count=affected_count,
        excluded_count=excluded_count,
    )


def dedupe_source_refs(
    refs: list[TacticalHouseViewSourceRef],
) -> list[TacticalHouseViewSourceRef]:
    unique = {
        (ref.source_system, ref.source_type, ref.source_id, ref.source_version): ref for ref in refs
    }
    return [
        unique[key]
        for key in sorted(unique, key=lambda item: (item[0], item[1], item[2], item[3] or ""))
    ]


__all__ = [
    "candidate_exclusion_reasons",
    "candidate_inclusion_reason_codes",
    "dedupe_source_refs",
    "exposure_exclusion_reasons",
    "normalize_portfolio_type",
    "supportability",
]
