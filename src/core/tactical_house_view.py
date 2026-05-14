"""Tactical house-view affected-cohort source product."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, cast

from pydantic import BaseModel, Field, model_validator

from src.core.common.canonical import hash_canonical_payload, strip_keys

TacticalHouseViewAction = Literal["INCREASE", "REDUCE", "REVIEW", "EXCLUDE"]
TacticalHouseViewAlignment = Literal["OVERWEIGHT", "UNDERWEIGHT", "ALIGNED", "UNKNOWN"]
TacticalHouseViewSupportabilityState = Literal["READY", "EMPTY", "BLOCKED"]


class TacticalHouseViewSourceRef(BaseModel):
    source_system: str = Field(
        description="System that owns the source evidence.",
        examples=["lotus-core"],
    )
    source_type: str = Field(
        description="Source product, artifact, or evidence type.",
        examples=["HoldingsAsOf"],
    )
    source_id: str = Field(
        description="Stable source identifier.",
        examples=["holdings:PB_SG_GLOBAL_BAL_001:2026-05-14"],
    )
    source_version: str | None = Field(
        default=None,
        description="Source contract or product version when available.",
        examples=["v1"],
    )
    content_hash: str | None = Field(
        default=None,
        description="Canonical source content hash when available.",
        examples=["sha256:source-evidence"],
    )


class TacticalHouseViewCandidatePortfolio(BaseModel):
    portfolio_id: str = Field(description="Candidate portfolio identifier.")
    mandate_id: str | None = Field(
        default=None,
        description="Mandate identifier when supplied by the source owner.",
    )
    portfolio_type: str = Field(
        description="Source-owned portfolio type used for DPM/discretionary eligibility.",
        examples=["DPM"],
    )
    discretionary_mandate: bool = Field(
        description="Whether source evidence says the portfolio is discretionary or managed."
    )
    booking_center_code: str | None = Field(
        default=None,
        description="Booking center or market context for cohort review.",
        examples=["Singapore"],
    )
    current_exposure_weight: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Optional source-owned exposure weight to the tactical theme.",
        examples=["0.18"],
    )
    alignment_signal: TacticalHouseViewAlignment = Field(
        default="UNKNOWN",
        description="Source-supplied alignment posture against the tactical house view.",
    )
    source_refs: list[TacticalHouseViewSourceRef] = Field(
        description="Source refs proving candidate identity and relevant exposure posture."
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Source-supplied bounded candidate reason codes.",
    )

    @model_validator(mode="after")
    def validate_candidate_source_refs(self) -> "TacticalHouseViewCandidatePortfolio":
        if not self.source_refs:
            raise ValueError("candidate source_refs must contain at least one source ref")
        return self


class TacticalHouseViewDefinition(BaseModel):
    tactical_view_id: str = Field(description="Bank tactical house-view identifier.")
    tactical_view_version: str = Field(description="Immutable tactical house-view version.")
    theme_id: str = Field(description="Tactical theme or recommendation identifier.")
    as_of_date: str = Field(description="House-view business as-of date.")
    target_action: TacticalHouseViewAction = Field(
        description="Bank tactical action being evaluated for affected portfolios."
    )
    rationale: str = Field(description="Bank-authored rationale for the tactical house view.")
    source_refs: list[TacticalHouseViewSourceRef] = Field(
        description="Governed source refs for the house-view decision."
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded house-view reason codes.",
    )

    @model_validator(mode="after")
    def validate_definition_source_refs(self) -> "TacticalHouseViewDefinition":
        if not self.source_refs:
            raise ValueError("tactical house-view source_refs must contain at least one source ref")
        return self


class TacticalHouseViewCohortRequest(BaseModel):
    tactical_view: TacticalHouseViewDefinition = Field(
        description="Governed bank tactical house-view instruction."
    )
    candidate_portfolios: list[TacticalHouseViewCandidatePortfolio] = Field(
        description=(
            "Caller-supplied source-backed candidate portfolios. This product does not discover "
            "the global portfolio universe."
        )
    )
    eligible_portfolio_types: list[str] = Field(
        default_factory=lambda: ["DPM", "DISCRETIONARY"],
        description="Portfolio types eligible for Manage consumption.",
    )
    min_exposure_weight: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Optional minimum source-owned exposure weight required for inclusion.",
    )
    correlation_id: str = Field(description="Caller correlation identifier.")

    @model_validator(mode="after")
    def validate_request(self) -> "TacticalHouseViewCohortRequest":
        if not self.candidate_portfolios:
            raise ValueError("candidate_portfolios must contain at least one candidate")
        if not self.eligible_portfolio_types:
            raise ValueError("eligible_portfolio_types must contain at least one value")
        return self


class TacticalHouseViewAffectedPortfolio(BaseModel):
    portfolio_id: str = Field(description="Affected portfolio identifier.")
    mandate_id: str | None = Field(default=None, description="Mandate identifier when available.")
    inclusion_reason_codes: list[str] = Field(description="Bounded inclusion reason codes.")
    source_refs: list[TacticalHouseViewSourceRef] = Field(description="Preserved source refs.")


class TacticalHouseViewExcludedPortfolio(BaseModel):
    portfolio_id: str = Field(description="Excluded portfolio identifier.")
    exclusion_reason_codes: list[str] = Field(description="Bounded exclusion reason codes.")
    source_refs: list[TacticalHouseViewSourceRef] = Field(description="Preserved source refs.")


class TacticalHouseViewSupportability(BaseModel):
    state: TacticalHouseViewSupportabilityState = Field(description="Cohort supportability state.")
    reason_codes: list[str] = Field(description="Bounded supportability reason codes.")
    evaluated_candidate_count: int = Field(
        ge=0,
        description="Number of source-backed candidate portfolios evaluated.",
    )
    affected_count: int = Field(ge=0, description="Number of affected portfolios returned.")
    excluded_count: int = Field(ge=0, description="Number of excluded portfolios returned.")


class TacticalHouseViewAffectedCohort(BaseModel):
    product_name: Literal["TacticalHouseViewAffectedCohort"] = Field(
        default="TacticalHouseViewAffectedCohort",
        description="Domain data product emitted by lotus-advise.",
    )
    product_version: Literal["v1"] = Field(default="v1", description="Product version.")
    cohort_id: str = Field(description="Stable content-addressed cohort identifier.")
    tactical_view_id: str = Field(description="Bank tactical house-view identifier.")
    tactical_view_version: str = Field(description="House-view version.")
    theme_id: str = Field(description="Tactical theme identifier.")
    as_of_date: str = Field(description="Cohort business as-of date.")
    target_action: TacticalHouseViewAction = Field(description="Tactical action evaluated.")
    affected_portfolios: list[TacticalHouseViewAffectedPortfolio] = Field(
        description="Source-backed portfolios affected by the tactical house view."
    )
    excluded_portfolios: list[TacticalHouseViewExcludedPortfolio] = Field(
        description="Source-backed portfolios excluded from the cohort."
    )
    supportability: TacticalHouseViewSupportability = Field(
        description="Product supportability posture."
    )
    source_refs: list[TacticalHouseViewSourceRef] = Field(
        description="House-view and candidate source refs preserved for consumers."
    )
    content_hash: str = Field(description="Canonical hash of this cohort payload.")
    generated_at: str = Field(description="UTC generation timestamp.")
    correlation_id: str = Field(description="Correlation identifier.")


def build_tactical_house_view_affected_cohort(
    request: TacticalHouseViewCohortRequest,
    *,
    generated_at: datetime | None = None,
) -> TacticalHouseViewAffectedCohort:
    """Build a deterministic tactical house-view cohort without source-fact recalculation."""

    generated_at = generated_at or datetime.now(timezone.utc)
    eligible_types = {value.upper() for value in request.eligible_portfolio_types}
    affected: list[TacticalHouseViewAffectedPortfolio] = []
    excluded: list[TacticalHouseViewExcludedPortfolio] = []

    for candidate in request.candidate_portfolios:
        exclusion_reasons = _candidate_exclusion_reasons(
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
                inclusion_reason_codes=_candidate_inclusion_reason_codes(candidate),
                source_refs=candidate.source_refs,
            )
        )

    supportability = _supportability(
        evaluated_candidate_count=len(request.candidate_portfolios),
        affected_count=len(affected),
        excluded_count=len(excluded),
    )
    source_refs = _dedupe_source_refs(
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
        supportability=supportability,
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


def _candidate_exclusion_reasons(
    *,
    candidate: TacticalHouseViewCandidatePortfolio,
    eligible_types: set[str],
    min_exposure_weight: Decimal | None,
) -> list[str]:
    reasons: list[str] = []
    if candidate.portfolio_type.upper() not in eligible_types:
        reasons.append("TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPE_NOT_ELIGIBLE")
    if not candidate.discretionary_mandate:
        reasons.append("TACTICAL_HOUSE_VIEW_NON_DISCRETIONARY_MANDATE")
    if candidate.alignment_signal == "ALIGNED":
        reasons.append("TACTICAL_HOUSE_VIEW_ALREADY_ALIGNED")
    if candidate.alignment_signal == "UNKNOWN":
        reasons.append("TACTICAL_HOUSE_VIEW_ALIGNMENT_UNKNOWN")
    if min_exposure_weight is not None and candidate.current_exposure_weight is None:
        reasons.append("TACTICAL_HOUSE_VIEW_EXPOSURE_EVIDENCE_MISSING")
    if (
        min_exposure_weight is not None
        and candidate.current_exposure_weight is not None
        and candidate.current_exposure_weight < min_exposure_weight
    ):
        reasons.append("TACTICAL_HOUSE_VIEW_EXPOSURE_BELOW_MINIMUM")
    return reasons


def _candidate_inclusion_reason_codes(
    candidate: TacticalHouseViewCandidatePortfolio,
) -> list[str]:
    reasons = {
        "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
        f"TACTICAL_HOUSE_VIEW_{candidate.alignment_signal}",
        *candidate.reason_codes,
    }
    return sorted(reasons)


def _supportability(
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


def _dedupe_source_refs(
    refs: list[TacticalHouseViewSourceRef],
) -> list[TacticalHouseViewSourceRef]:
    unique = {
        (ref.source_system, ref.source_type, ref.source_id, ref.source_version): ref for ref in refs
    }
    return [
        unique[key]
        for key in sorted(unique, key=lambda item: (item[0], item[1], item[2], item[3] or ""))
    ]
