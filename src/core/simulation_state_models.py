from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_serializer

from src.core.portfolio_models import CashBalance, Money


def _quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


class AllocationMetric(BaseModel):
    key: str = Field(description="Allocation bucket key (instrument, asset class, or tag value).")
    weight: Decimal = Field(description="Weight of the bucket in portfolio total value.")
    value: Money = Field(description="Monetary value of the bucket.")

    @field_serializer("weight")
    def serialize_weight(self, value: Decimal) -> Decimal:
        return value


ProposalAllocationDimension = Literal[
    "asset_class",
    "currency",
    "sector",
    "country",
    "region",
    "product_type",
    "rating",
]


class ProposalAllocationBucket(BaseModel):
    key: str = Field(description="Allocation bucket key for the requested dimension.")
    weight: Decimal = Field(description="Bucket weight in total portfolio value.")
    value: Money = Field(description="Bucket value in the portfolio reporting currency.")
    position_count: int = Field(
        ge=0,
        description="Number of position or cash rows contributing to this bucket.",
    )

    @field_serializer("weight")
    def serialize_weight(self, value: Decimal) -> Decimal:
        return value


class ProposalAllocationView(BaseModel):
    dimension: ProposalAllocationDimension = Field(
        description="Front-office allocation dimension used for proposal before/after review."
    )
    total_value: Money = Field(description="Total value used as the allocation denominator.")
    buckets: List[ProposalAllocationBucket] = Field(
        default_factory=list,
        description="Sorted allocation buckets for this dimension.",
    )


class ProposalAllocationLens(BaseModel):
    contract_version: str = Field(
        default="advisory-simulation.v1",
        description="Simulation contract version that governs the allocation lens.",
    )
    calculator_version: str = Field(
        default="lotus-core.allocation-calculator.v1",
        description="Internal calculator version for replay and audit evidence.",
    )
    dimensions: List[ProposalAllocationDimension] = Field(
        default_factory=lambda: [
            "asset_class",
            "currency",
            "sector",
            "country",
            "region",
            "product_type",
            "rating",
        ],
        description="Curated proposal allocation dimensions included in before/after states.",
    )
    source: Literal["LOTUS_CORE", "LOTUS_ADVISE_LOCAL_FALLBACK"] = Field(
        default="LOTUS_CORE",
        description="Authoritative service that computed the allocation lens.",
    )


class PositionSummary(BaseModel):
    instrument_id: str = Field(description="Instrument identifier.")
    quantity: Decimal = Field(description="Simulated quantity.")
    instrument_currency: str = Field(description="Instrument trading currency.")
    asset_class: str = Field(default="UNKNOWN", description="Asset-class label for aggregation.")
    price: Optional[Money] = Field(default=None, description="Price used in valuation.")
    value_in_instrument_ccy: Money = Field(description="Position value in instrument currency.")
    value_in_base_ccy: Money = Field(description="Position value converted to base currency.")
    weight: Decimal = Field(description="Portfolio weight in base currency terms.")

    @field_serializer("weight")
    def serialize_weight(self, value: Decimal) -> Decimal:
        return _quantize_ratio(value)


class SimulatedState(BaseModel):
    total_value: Money = Field(description="Total simulated portfolio value in base currency.")
    cash_balances: List[CashBalance] = Field(
        default_factory=list, description="Cash balances by currency."
    )
    positions: List[PositionSummary] = Field(
        default_factory=list, description="Position-level simulated state."
    )
    allocation_by_asset_class: List[AllocationMetric] = Field(
        default_factory=list,
        description="Allocation grouped by asset class plus CASH bucket.",
    )
    allocation_by_instrument: List[AllocationMetric] = Field(
        default_factory=list,
        description="Allocation grouped by instrument id.",
    )
    allocation: List[AllocationMetric] = Field(
        default_factory=list,
        description="Legacy allocation view, aligned to allocation_by_instrument.",
    )
    allocation_by_attribute: Dict[str, List[AllocationMetric]] = Field(
        default_factory=dict,
        description="Allocation grouped by configured shelf attributes.",
    )
    allocation_views: List[ProposalAllocationView] = Field(
        default_factory=list,
        description=(
            "Canonical proposal allocation views computed by the lotus-core allocation "
            "calculator for curated front-office dimensions."
        ),
    )


__all__ = [
    "AllocationMetric",
    "PositionSummary",
    "ProposalAllocationBucket",
    "ProposalAllocationDimension",
    "ProposalAllocationLens",
    "ProposalAllocationView",
    "SimulatedState",
]
