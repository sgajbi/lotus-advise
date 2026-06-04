from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
        description=(
            "Source-owned portfolio type used for discretionary portfolio-management eligibility."
        ),
        examples=["DISCRETIONARY"],
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
        default_factory=lambda: ["DISCRETIONARY", "MANAGED"],
        description="Portfolio types eligible for downstream portfolio-management consumption.",
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
]
