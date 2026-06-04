from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.portfolio_models import Money


class ProposalArtifactTradeRationale(BaseModel):
    code: str = Field(
        description="Machine-readable trade rationale code.", examples=["MANUAL_PROPOSAL"]
    )
    message: str = Field(
        description="Deterministic rationale message for trade presentation.",
        examples=["Manual advisory trade from proposal simulation."],
    )


class ProposalArtifactTrade(BaseModel):
    intent_id: str = Field(description="Intent identifier from proposal output.", examples=["oi_1"])
    type: Literal["SECURITY_TRADE"] = Field(
        description="Artifact trade entry type.", examples=["SECURITY_TRADE"]
    )
    instrument_id: str = Field(description="Security instrument id.", examples=["US_EQ_ETF"])
    side: Literal["BUY", "SELL"] = Field(description="Trade side.", examples=["BUY"])
    quantity: str = Field(description="Trade quantity as a decimal string.", examples=["10"])
    estimated_notional: Optional[Money] = Field(
        default=None,
        description="Estimated trade notional in instrument currency.",
    )
    estimated_notional_base: Optional[Money] = Field(
        default=None,
        description="Estimated trade notional in portfolio base currency.",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Intent dependencies that must execute first.",
        examples=[["oi_fx_1"]],
    )
    rationale: ProposalArtifactTradeRationale = Field(description="Deterministic trade rationale.")


class ProposalArtifactFx(BaseModel):
    intent_id: str = Field(description="FX intent identifier.", examples=["oi_fx_1"])
    pair: str = Field(description="FX pair identifier.", examples=["USD/SGD"])
    buy_amount: str = Field(
        description="Buy amount in buy currency as a decimal string.",
        examples=["1500.00"],
    )
    sell_amount_estimated: str = Field(
        description="Estimated sell amount in funding currency as a decimal string.",
        examples=["2025.00"],
    )
    rate: Optional[str] = Field(
        default=None,
        description="Resolved FX rate string when available from market snapshot.",
        examples=["1.3500"],
    )


class ProposalArtifactExecutionNote(BaseModel):
    code: str = Field(description="Execution note code.", examples=["DEPENDENCY"])
    text: str = Field(
        description="Deterministic execution note text.",
        examples=["One or more BUY intents depend on generated FX intents."],
    )


class ProposalArtifactTradesAndFunding(BaseModel):
    trade_list: List[ProposalArtifactTrade] = Field(
        default_factory=list,
        description="Deterministically ordered security trades.",
    )
    fx_list: List[ProposalArtifactFx] = Field(
        default_factory=list,
        description="Deterministically ordered FX intents for funding.",
    )
    ordering_policy: str = Field(
        description="Execution ordering policy used when rendering the package.",
        examples=["CASH_FLOW->SELL->FX->BUY"],
    )
    execution_notes: List[ProposalArtifactExecutionNote] = Field(
        default_factory=list,
        description="Structured deterministic execution notes.",
    )
