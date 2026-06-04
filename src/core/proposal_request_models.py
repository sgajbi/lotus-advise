from __future__ import annotations

from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.advisory.alternatives_models import ProposalAlternativesRequest
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.engine_options_models import EngineOptions
from src.core.portfolio_models import (
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    ReferenceModel,
    ShelfEntry,
)


def _is_python_float(candidate: object) -> bool:
    type_name = candidate.__class__.__name__
    if type_name == "float":
        return True
    return False


class ProposedCashFlow(BaseModel):
    intent_type: Literal["CASH_FLOW"] = Field(
        default="CASH_FLOW",
        description="Intent discriminator for advisory cash-flow proposals.",
        examples=["CASH_FLOW"],
    )
    currency: str = Field(description="Cash-flow currency code.", examples=["USD"])
    amount: Decimal = Field(
        description="Signed cash-flow amount as decimal string.",
        examples=["2000.00", "-500.00"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional advisor-entered narrative for this cash flow.",
        examples=["Client deposit before switch"],
    )

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float_amount(cls, v: object) -> object:
        if _is_python_float(v):
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: amount must be a decimal string")
        return v


class ProposedTrade(BaseModel):
    intent_type: Literal["SECURITY_TRADE"] = Field(
        default="SECURITY_TRADE",
        description="Intent discriminator for advisory security trades.",
        examples=["SECURITY_TRADE"],
    )
    side: Literal["BUY", "SELL"] = Field(description="Manual trade side.", examples=["BUY"])
    instrument_id: str = Field(
        description="Instrument identifier for manual trade.",
        examples=["EQ_GROWTH"],
    )
    quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description="Trade quantity. Required when `notional` is not provided.",
        examples=["40"],
    )
    notional: Optional[Money] = Field(
        default=None,
        description=(
            "Trade notional in instrument currency. Required when `quantity` is not provided."
        ),
        examples=[{"amount": "2000.00", "currency": "USD"}],
    )

    @field_validator("quantity", mode="before")
    @classmethod
    def reject_float_quantity(cls, v: object) -> object:
        if _is_python_float(v):
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: quantity must be a decimal string")
        return v

    @field_validator("notional", mode="before")
    @classmethod
    def reject_float_notional_amount(cls, v: object) -> object:
        if isinstance(v, dict) and _is_python_float(v.get("amount")):
            raise ValueError(
                "PROPOSAL_INVALID_TRADE_INPUT: notional.amount must be a decimal string"
            )
        return v

    @model_validator(mode="after")
    def validate_quantity_or_notional(self) -> "ProposedTrade":
        if self.quantity is None and self.notional is None:
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: quantity or notional is required")
        if self.quantity is not None and self.notional is not None:
            raise ValueError(
                "PROPOSAL_INVALID_TRADE_INPUT: provide either quantity or notional, not both"
            )
        if self.notional is not None and self.notional.amount <= Decimal("0"):
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: notional.amount must be greater than 0")
        return self


class ProposalSimulateRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                    "positions": [{"instrument_id": "EQ_LEGACY", "quantity": "100"}],
                    "cash_balances": [{"currency": "USD", "amount": "5000.00"}],
                },
                "market_data_snapshot": {
                    "prices": [
                        {"instrument_id": "EQ_LEGACY", "price": "100.00", "currency": "USD"},
                        {"instrument_id": "EQ_GROWTH", "price": "50.00", "currency": "USD"},
                    ],
                    "fx_rates": [],
                },
                "shelf_entries": [
                    {"instrument_id": "EQ_LEGACY", "status": "APPROVED"},
                    {"instrument_id": "EQ_GROWTH", "status": "APPROVED"},
                ],
                "options": {
                    "enable_proposal_simulation": True,
                    "proposal_apply_cash_flows_first": True,
                    "proposal_block_negative_cash": True,
                    "block_on_missing_prices": True,
                    "block_on_missing_fx": True,
                },
                "proposed_cash_flows": [
                    {
                        "intent_type": "CASH_FLOW",
                        "currency": "USD",
                        "amount": "2000.00",
                        "description": "Client top-up",
                    }
                ],
                "proposed_trades": [
                    {
                        "intent_type": "SECURITY_TRADE",
                        "side": "BUY",
                        "instrument_id": "EQ_GROWTH",
                        "quantity": "40",
                    }
                ],
            }
        }
    }

    portfolio_snapshot: PortfolioSnapshot = Field(
        description="Current portfolio holdings and cash balances.",
        examples=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_LEGACY", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "5000.00"}],
            }
        ],
    )
    market_data_snapshot: MarketDataSnapshot = Field(
        description="Price and FX snapshot used for proposal simulation.",
        examples=[
            {
                "prices": [
                    {"instrument_id": "EQ_LEGACY", "price": "100.00", "currency": "USD"},
                    {"instrument_id": "EQ_GROWTH", "price": "50.00", "currency": "USD"},
                ],
                "fx_rates": [],
            }
        ],
    )
    shelf_entries: List[ShelfEntry] = Field(
        description="Instrument eligibility and policy metadata.",
        examples=[
            [
                {"instrument_id": "EQ_LEGACY", "status": "APPROVED"},
                {"instrument_id": "EQ_GROWTH", "status": "APPROVED"},
            ]
        ],
    )
    options: EngineOptions = Field(
        default_factory=EngineOptions,
        description="Request-level engine behavior and feature toggles.",
        examples=[
            {
                "enable_proposal_simulation": True,
                "proposal_apply_cash_flows_first": True,
                "proposal_block_negative_cash": True,
            }
        ],
    )
    proposed_cash_flows: List[ProposedCashFlow] = Field(
        default_factory=list,
        description="Advisor-entered cash flow instructions.",
        examples=[[{"intent_type": "CASH_FLOW", "currency": "USD", "amount": "2000.00"}]],
    )
    proposed_trades: List[ProposedTrade] = Field(
        default_factory=list,
        description="Advisor-entered manual security trade instructions.",
        examples=[
            [
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_GROWTH",
                    "quantity": "40",
                }
            ]
        ],
    )
    reference_model: Optional[ReferenceModel] = Field(
        default=None,
        description="Optional reference model used for advisory drift analytics.",
    )
    alternatives_request: ProposalAlternativesRequest | None = Field(
        default=None,
        description=(
            "Optional backend-owned alternatives request for proposal comparison generation."
        ),
    )
    narrative_request: ProposalNarrativeRequest | None = Field(
        default=None,
        description=(
            "Optional advisor-review proposal narrative request. Supports deterministic template "
            "mode and Slice 7 opt-in `AI_ASSISTED_DRAFT`; client-ready commentary remains gated."
        ),
    )


__all__ = [
    "ProposalSimulateRequest",
    "ProposedCashFlow",
    "ProposedTrade",
]
