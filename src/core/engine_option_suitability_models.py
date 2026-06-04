from __future__ import annotations

from decimal import Decimal
from typing import Dict, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GroupConstraint(BaseModel):
    max_weight: Decimal = Field(
        description="Maximum allowed aggregate weight for the tagged group."
    )

    @field_validator("max_weight")
    @classmethod
    def validate_max_weight(cls, v: Decimal) -> Decimal:
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("max_weight must be between 0 and 1 inclusive")
        return v


class SuitabilityThresholds(BaseModel):
    single_position_max_weight: Decimal = Field(
        default=Decimal("0.10"),
        ge=0,
        le=1,
        description="Maximum advisory suitability weight per single instrument.",
        examples=["0.10"],
    )
    issuer_max_weight: Decimal = Field(
        default=Decimal("0.20"),
        ge=0,
        le=1,
        description="Maximum advisory suitability aggregate weight per issuer.",
        examples=["0.20"],
    )
    max_weight_by_liquidity_tier: Dict[str, Decimal] = Field(
        default_factory=lambda: {"L4": Decimal("0.10"), "L5": Decimal("0.05")},
        description=(
            "Maximum advisory suitability aggregate weight by liquidity tier, "
            "for example {'L4': '0.10', 'L5': '0.05'}."
        ),
        examples=[{"L4": "0.10", "L5": "0.05"}],
    )
    cash_band_min_weight: Decimal = Field(
        default=Decimal("0.01"),
        ge=0,
        le=1,
        description="Minimum advisory suitability cash weight.",
        examples=["0.01"],
    )
    cash_band_max_weight: Decimal = Field(
        default=Decimal("0.05"),
        ge=0,
        le=1,
        description="Maximum advisory suitability cash weight.",
        examples=["0.05"],
    )
    data_quality_issue_severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        default="MEDIUM",
        description="Severity used for suitability data-quality issues.",
        examples=["MEDIUM"],
    )

    @field_validator("max_weight_by_liquidity_tier")
    @classmethod
    def validate_max_weight_by_liquidity_tier(cls, v: Dict[str, Decimal]) -> Dict[str, Decimal]:
        for tier, value in v.items():
            if tier not in {"L1", "L2", "L3", "L4", "L5"}:
                raise ValueError("liquidity tier keys must be one of L1, L2, L3, L4, L5")
            if value < Decimal("0") or value > Decimal("1"):
                raise ValueError("liquidity-tier max weights must be between 0 and 1 inclusive")
        return v

    @model_validator(mode="after")
    def validate_cash_band(self) -> "SuitabilityThresholds":
        if self.cash_band_min_weight > self.cash_band_max_weight:
            raise ValueError("suitability cash band min cannot exceed max")
        return self


__all__ = ["GroupConstraint", "SuitabilityThresholds"]
