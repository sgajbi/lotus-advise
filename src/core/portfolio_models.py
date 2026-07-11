from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.core.source_provenance_models import SourceProvenanceRecord


class Money(BaseModel):
    amount: Decimal = Field(
        description="Monetary amount as decimal string/number.",
        examples=["1000.50"],
    )
    currency: str = Field(
        description="ISO currency code (for example USD, SGD).",
        examples=["USD"],
    )


class FxRate(BaseModel):
    pair: str = Field(
        description="Currency pair in BASE/QUOTE style used by engine lookup.",
        examples=["USD/SGD"],
    )
    rate: Decimal = Field(description="FX conversion rate for the pair.", examples=["1.35"])


class TaxLot(BaseModel):
    lot_id: str = Field(
        description="Unique lot identifier within instrument.", examples=["LOT_001"]
    )
    quantity: Decimal = Field(ge=0, description="Lot quantity.", examples=["50"])
    unit_cost: Money = Field(description="Per-unit cost basis for the lot.")
    purchase_date: str = Field(description="Lot purchase date (ISO date string).")


class Position(BaseModel):
    instrument_id: str = Field(description="Unique instrument identifier.", examples=["AAPL"])
    quantity: Decimal = Field(description="Held quantity before simulation.", examples=["100"])
    market_value: Optional[Money] = Field(
        default=None,
        description="Optional trusted market value used when valuation_mode=TRUST_SNAPSHOT.",
    )
    lots: List[TaxLot] = Field(
        default_factory=list,
        description="Optional tax-lot breakdown for tax-aware sell allocation.",
    )

    @model_validator(mode="after")
    def validate_lot_quantity_total(self) -> "Position":
        if not self.lots:
            return self
        total = sum((lot.quantity for lot in self.lots), Decimal("0"))
        if abs(total - self.quantity) > Decimal("0.0001"):
            raise ValueError(
                "sum(lot.quantity) must equal position.quantity within tolerance 0.0001"
            )
        return self


class CashBalance(BaseModel):
    currency: str = Field(description="Cash currency code.", examples=["USD"])
    amount: Decimal = Field(
        description="Available cash amount used by current simulation stages.",
        examples=["25000"],
    )
    settled: Optional[Decimal] = Field(
        default=None,
        description="Optional settled cash amount used by settlement-aware ladder.",
    )
    pending: Optional[Decimal] = Field(
        default=None,
        description="Optional pending cash amount for informational reporting.",
    )


class PortfolioSnapshot(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_id": "pf_1",
                "base_currency": "USD",
                "positions": [{"instrument_id": "AAPL", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "5000"}],
            }
        }
    }

    snapshot_id: Optional[str] = Field(
        default=None,
        description="Optional immutable snapshot identifier for lineage.",
    )
    source_provenance: Optional[SourceProvenanceRecord] = Field(
        default=None,
        description="Optional upstream portfolio source provenance for audit and replay.",
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    base_currency: str = Field(
        description="Base reporting currency for valuation and rules.",
        examples=["USD"],
    )
    positions: List[Position] = Field(default_factory=list, description="Current held positions.")
    cash_balances: List[CashBalance] = Field(
        default_factory=list,
        description="Current portfolio cash balances by currency.",
    )


class Price(BaseModel):
    instrument_id: str = Field(
        description="Instrument identifier for the price row.", examples=["AAPL"]
    )
    price: Decimal = Field(
        description="Last/mark price used in valuation and sizing.", examples=["180.25"]
    )
    currency: str = Field(description="Currency of the price.", examples=["USD"])


class MarketDataSnapshot(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "prices": [{"instrument_id": "AAPL", "price": "180.25", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            }
        }
    }

    snapshot_id: Optional[str] = Field(
        default=None,
        description="Optional immutable market-data snapshot identifier for lineage.",
    )
    source_provenance: Optional[SourceProvenanceRecord] = Field(
        default=None,
        description="Optional upstream market-data source provenance for audit and replay.",
    )
    prices: List[Price] = Field(default_factory=list, description="Instrument prices.")
    fx_rates: List[FxRate] = Field(
        default_factory=list, description="FX rates for currency conversion."
    )


class ModelTarget(BaseModel):
    instrument_id: str = Field(
        description="Instrument identifier in model target.", examples=["AAPL"]
    )
    weight: Decimal = Field(
        description="Target portfolio weight for the instrument.", examples=["0.25"]
    )


class ModelPortfolio(BaseModel):
    targets: List[ModelTarget] = Field(description="List of model target weights.")


class ReferenceAssetClassTarget(BaseModel):
    asset_class: str = Field(description="Reference model asset-class bucket.")
    weight: Decimal = Field(description="Target weight for the asset-class bucket.")


class ReferenceInstrumentTarget(BaseModel):
    instrument_id: str = Field(description="Reference model instrument identifier.")
    weight: Decimal = Field(description="Target weight for the instrument bucket.")


class ReferenceModel(BaseModel):
    model_id: str = Field(description="Reference model identifier.")
    as_of: str = Field(description="Reference model as-of date.")
    base_currency: str = Field(description="Reference model base currency.")
    asset_class_targets: List[ReferenceAssetClassTarget] = Field(
        default_factory=list,
        description="Reference target weights by asset class.",
    )
    instrument_targets: List[ReferenceInstrumentTarget] = Field(
        default_factory=list,
        description="Optional reference target weights by instrument.",
    )


class ShelfEntry(BaseModel):
    instrument_id: str = Field(
        description="Instrument identifier in product shelf.", examples=["AAPL"]
    )
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"]
    asset_class: str = Field(
        default="UNKNOWN", description="Asset-class label for aggregation/reporting."
    )
    issuer_id: Optional[str] = Field(
        default=None,
        description="Issuer identifier used for concentration analytics and suitability checks.",
        examples=["ISSUER_TECH_1"],
    )
    liquidity_tier: Optional[Literal["L1", "L2", "L3", "L4", "L5"]] = Field(
        default=None,
        description="Liquidity tier label used for suitability liquidity exposure checks.",
        examples=["L1", "L4"],
    )
    settlement_days: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Settlement lag in business-day offsets used by settlement ladder.",
    )
    min_notional: Optional[Money] = Field(
        default=None,
        description="Optional per-instrument minimum trade notional.",
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Attribute tags used for group constraints (for example sector, region).",
    )


__all__ = [
    "CashBalance",
    "FxRate",
    "MarketDataSnapshot",
    "ModelPortfolio",
    "ModelTarget",
    "Money",
    "PortfolioSnapshot",
    "Position",
    "Price",
    "ReferenceAssetClassTarget",
    "ReferenceInstrumentTarget",
    "ReferenceModel",
    "ShelfEntry",
    "TaxLot",
]
