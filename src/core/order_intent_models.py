from __future__ import annotations

from decimal import Decimal
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from src.core.portfolio_models import Money


class IntentRationale(BaseModel):
    code: str = Field(description="Short rationale code for generated intent.")
    message: str = Field(description="Human-readable rationale message.")


class SecurityTradeIntent(BaseModel):
    intent_type: Literal["SECURITY_TRADE"] = Field(
        default="SECURITY_TRADE",
        description="Intent discriminator.",
    )
    intent_id: str = Field(description="Intent identifier unique within run.")
    instrument_id: str = Field(description="Instrument identifier for trade.")
    side: Literal["BUY", "SELL"] = Field(description="Trade side.")
    quantity: Optional[Decimal] = Field(default=None, description="Trade quantity.")
    notional: Optional[Money] = Field(
        default=None, description="Trade notional in instrument currency."
    )
    notional_base: Optional[Money] = Field(
        default=None, description="Trade notional converted to base currency."
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Intent ids that must execute first."
    )
    rationale: Optional[IntentRationale] = Field(
        default=None, description="Rationale for this intent."
    )
    constraints_applied: List[str] = Field(
        default_factory=list,
        description="Constraint labels applied during sizing.",
    )


class FxSpotIntent(BaseModel):
    intent_type: Literal["FX_SPOT"] = Field(default="FX_SPOT", description="Intent discriminator.")
    intent_id: str = Field(description="Intent identifier unique within run.")
    pair: str = Field(description="FX pair of the conversion intent.")
    buy_currency: str = Field(description="Currency bought by this FX trade.")
    buy_amount: Decimal = Field(description="Estimated amount bought.")
    sell_currency: str = Field(description="Currency sold by this FX trade.")
    sell_amount_estimated: Decimal = Field(description="Estimated amount sold.")
    dependencies: List[str] = Field(
        default_factory=list, description="Intent ids that must execute first."
    )
    rationale: Optional[IntentRationale] = Field(
        default=None, description="Rationale for this FX intent."
    )


class CashFlowIntent(BaseModel):
    intent_type: Literal["CASH_FLOW"] = Field(
        default="CASH_FLOW",
        description="Intent discriminator.",
        examples=["CASH_FLOW"],
    )
    intent_id: str = Field(description="Intent identifier unique within run.", examples=["oi_cf_1"])
    currency: str = Field(description="Cash-flow currency code.", examples=["USD"])
    amount: Decimal = Field(description="Signed cash-flow amount.", examples=["2000.00"])
    description: Optional[str] = Field(
        default=None,
        description="Optional advisor-entered note.",
        examples=["Client top-up"],
    )


OrderIntent = Union[SecurityTradeIntent, FxSpotIntent]
ProposalOrderIntent = Union[CashFlowIntent, FxSpotIntent, SecurityTradeIntent]


__all__ = [
    "CashFlowIntent",
    "FxSpotIntent",
    "IntentRationale",
    "OrderIntent",
    "ProposalOrderIntent",
    "SecurityTradeIntent",
]
