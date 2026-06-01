from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.portfolio_models import Money


class ExcludedInstrument(BaseModel):
    instrument_id: str = Field(description="Instrument excluded from buy/sell universe.")
    reason_code: str = Field(description="Reason code for exclusion.")
    details: Optional[str] = Field(
        default=None, description="Optional details for exclusion reason."
    )


class UniverseCoverage(BaseModel):
    price_coverage_pct: Decimal = Field(
        description="Price coverage percentage for required instruments."
    )
    fx_coverage_pct: Decimal = Field(
        description="FX coverage percentage for required currency pairs."
    )


class UniverseData(BaseModel):
    universe_id: str = Field(description="Universe identifier for the run.")
    eligible_for_buy: List[str] = Field(
        default_factory=list, description="Instrument ids eligible for buy intents."
    )
    eligible_for_sell: List[str] = Field(
        default_factory=list,
        description="Instrument ids eligible for sell intents.",
    )
    excluded: List[ExcludedInstrument] = Field(
        default_factory=list,
        description="Instruments excluded by shelf/data constraints.",
    )
    coverage: UniverseCoverage = Field(description="Market-data coverage metrics.")


class TargetInstrument(BaseModel):
    model_config = {"protected_namespaces": ()}
    instrument_id: str = Field(description="Instrument identifier in target trace.")
    model_weight: Decimal = Field(description="Input model weight.")
    final_weight: Decimal = Field(description="Final constrained target weight.")
    final_value: Money = Field(description="Final constrained target value in base currency.")
    tags: List[str] = Field(
        default_factory=list, description="Trace tags explaining target adjustments."
    )


class TargetData(BaseModel):
    target_id: str = Field(description="Target stage identifier.")
    strategy: Dict[str, Any] = Field(description="Strategy metadata (currently minimal).")
    targets: List[TargetInstrument] = Field(description="Instrument-level target trace output.")


__all__ = [
    "ExcludedInstrument",
    "TargetData",
    "TargetInstrument",
    "UniverseCoverage",
    "UniverseData",
]
