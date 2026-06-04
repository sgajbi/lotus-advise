from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.advisory.alternatives_types import (
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
)


def _is_python_float(value: object) -> bool:
    return type(value) is type(0.1)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


class AlternativeMoneyConstraint(BaseModel):
    amount: Decimal = Field(
        description="Positive monetary amount used by alternatives constraints.",
        examples=["25000"],
    )
    currency: str = Field(
        description="ISO currency code used by the monetary constraint.",
        examples=["USD"],
    )

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float_amount(cls, value: object) -> object:
        if _is_python_float(value):
            raise ValueError(
                "ALTERNATIVES_INVALID_CONSTRAINT: amount must be provided as a decimal string"
            )
        return value

    @field_validator("amount")
    @classmethod
    def require_positive_amount(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("ALTERNATIVES_INVALID_CONSTRAINT: amount must be greater than 0")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ALTERNATIVES_INVALID_CONSTRAINT: currency is required")
        return normalized


class ProposalAlternativesConstraints(BaseModel):
    cash_floor: AlternativeMoneyConstraint | None = Field(
        default=None,
        description="Minimum cash floor that must remain after the alternative is applied.",
    )
    max_turnover_pct: Decimal | None = Field(
        default=None,
        description="Maximum permitted portfolio turnover percentage.",
        examples=["12.50"],
    )
    max_trade_count: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of generated trades allowed for the alternative.",
    )
    preserve_holdings: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that must remain held.",
    )
    restricted_instruments: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that must not appear in the alternative.",
    )
    do_not_buy: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that the strategy must not buy.",
    )
    do_not_sell: list[str] = Field(
        default_factory=list,
        description="Instrument identifiers that the strategy must not sell.",
    )
    allow_fx: bool = Field(
        default=True,
        description="Whether FX actions are permitted for the alternative.",
    )
    allowed_currencies: list[str] = Field(
        default_factory=list,
        description="Explicitly allowed target currencies when FX is permitted.",
    )
    mandate_restrictions: dict[str, Any] | None = Field(
        default=None,
        description="Optional mandate restrictions context for alternatives evaluation.",
    )
    client_preferences: dict[str, Any] | None = Field(
        default=None,
        description="Optional client preference context for alternatives evaluation.",
    )

    @field_validator("max_turnover_pct", mode="before")
    @classmethod
    def reject_float_turnover(cls, value: object) -> object:
        if _is_python_float(value):
            raise ValueError(
                "ALTERNATIVES_INVALID_CONSTRAINT: max_turnover_pct must be a decimal string"
            )
        return value

    @field_validator("max_turnover_pct")
    @classmethod
    def validate_turnover_range(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value < Decimal("0") or value > Decimal("100"):
            raise ValueError(
                "ALTERNATIVES_INVALID_CONSTRAINT: max_turnover_pct must be between 0 and 100"
            )
        return value

    @field_validator(
        "preserve_holdings",
        "restricted_instruments",
        "do_not_buy",
        "do_not_sell",
        mode="before",
    )
    @classmethod
    def normalize_instrument_lists(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip() for item in value])

    @field_validator("allowed_currencies", mode="before")
    @classmethod
    def normalize_currency_list(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip().upper() for item in value])


class ProposalAlternativesRequest(BaseModel):
    enabled: bool = Field(
        default=True,
        description="Whether alternatives generation is requested for this evaluation flow.",
    )
    objectives: list[AlternativeConstructionObjective] = Field(
        default_factory=list,
        description="Explicit advisor-requested construction objectives in priority order.",
    )
    constraints: ProposalAlternativesConstraints = Field(
        default_factory=ProposalAlternativesConstraints,
        description="Constraints that govern alternatives generation.",
    )
    max_alternatives: int = Field(
        default=3,
        ge=1,
        description="Maximum number of ranked alternatives to return.",
    )
    candidate_generation_policy_id: str | None = Field(
        default=None,
        description="Optional policy identifier controlling candidate generation behavior.",
    )
    ranking_policy_id: str | None = Field(
        default=None,
        description="Optional policy identifier controlling alternatives ranking behavior.",
    )
    include_rejected_candidates: bool = Field(
        default=True,
        description="Whether rejected alternatives should be retained in the response.",
    )
    evidence_requirements: list[AlternativeEvidenceRequirement] = Field(
        default_factory=list,
        description="Explicit upstream evidence requirements declared for this request.",
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description=(
            "Backend-issued alternative id selected in a later lifecycle or workspace write."
        ),
    )

    @field_validator("objectives", mode="before")
    @classmethod
    def dedupe_objectives(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip().upper() for item in value])

    @field_validator("evidence_requirements", mode="before")
    @classmethod
    def dedupe_evidence_requirements(cls, value: object) -> object:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return _dedupe_preserve_order([str(item).strip().upper() for item in value])


__all__ = [
    "AlternativeMoneyConstraint",
    "ProposalAlternativesConstraints",
    "ProposalAlternativesRequest",
]
