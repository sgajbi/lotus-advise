from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class DriftReferenceModelSummary(BaseModel):
    model_id: str = Field(description="Reference model identifier.")
    as_of: str = Field(description="Reference model as-of date.")
    base_currency: str = Field(description="Reference model base currency.")


class DriftBucketDetail(BaseModel):
    bucket: str = Field(description="Drift bucket key.")
    model_weight: Decimal = Field(description="Reference model weight for the bucket.")
    portfolio_weight_before: Decimal = Field(
        description="Before-state portfolio weight for the bucket."
    )
    portfolio_weight_after: Decimal = Field(
        description="After-state portfolio weight for the bucket."
    )
    drift_before: Decimal = Field(description="Signed before-state drift for the bucket.")
    drift_after: Decimal = Field(description="Signed after-state drift for the bucket.")
    abs_drift_before: Decimal = Field(description="Absolute before-state drift for the bucket.")
    abs_drift_after: Decimal = Field(description="Absolute after-state drift for the bucket.")
    improvement: Decimal = Field(description="Positive when absolute drift improves.")


class DriftDimensionAnalysis(BaseModel):
    drift_total_before: Decimal = Field(description="Total drift in before-state.")
    drift_total_after: Decimal = Field(description="Total drift in after-state.")
    drift_total_delta: Decimal = Field(
        description="After minus before drift total. Negative means improvement."
    )
    top_contributors_before: List[DriftBucketDetail] = Field(
        default_factory=list,
        description="Largest before-state drift contributors.",
    )
    buckets: List[DriftBucketDetail] = Field(
        default_factory=list,
        description="Deterministic drift details for all buckets.",
    )


class DriftHighlightEntry(BaseModel):
    bucket: str = Field(description="Highlighted drift bucket.")
    improvement: Decimal = Field(description="Improvement value for the highlighted bucket.")


class DriftUnmodeledExposure(BaseModel):
    bucket: str = Field(description="Bucket with model weight of zero.")
    portfolio_weight_before: Decimal = Field(description="Before-state exposure for the bucket.")
    portfolio_weight_after: Decimal = Field(description="After-state exposure for the bucket.")
    max_portfolio_weight: Decimal = Field(
        description="Max of before/after exposure for the bucket."
    )


class DriftHighlights(BaseModel):
    largest_improvements: List[DriftHighlightEntry] = Field(
        default_factory=list,
        description="Buckets with largest positive drift improvements.",
    )
    largest_deteriorations: List[DriftHighlightEntry] = Field(
        default_factory=list,
        description="Buckets with largest drift deteriorations.",
    )
    unmodeled_exposures: List[DriftUnmodeledExposure] = Field(
        default_factory=list,
        description="Buckets where model weight is zero and exposure exceeds threshold.",
    )


class DriftAnalysis(BaseModel):
    reference_model: DriftReferenceModelSummary = Field(
        description="Reference model identifier details."
    )
    asset_class: DriftDimensionAnalysis = Field(description="Asset-class drift analytics.")
    instrument: Optional[DriftDimensionAnalysis] = Field(
        default=None,
        description="Instrument drift analytics when instrument targets are provided.",
    )
    highlights: DriftHighlights = Field(description="Deterministic advisory highlights.")


__all__ = [
    "DriftAnalysis",
    "DriftBucketDetail",
    "DriftDimensionAnalysis",
    "DriftHighlightEntry",
    "DriftHighlights",
    "DriftReferenceModelSummary",
    "DriftUnmodeledExposure",
]
