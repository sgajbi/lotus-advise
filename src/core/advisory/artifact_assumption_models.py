from typing import List

from pydantic import BaseModel, Field


class ProposalArtifactPricingAssumptions(BaseModel):
    market_data_snapshot_id: str = Field(
        description="Market-data snapshot identifier used by simulation.",
        examples=["md_2026_02_19"],
    )
    prices_as_of: str = Field(
        description="Price snapshot as-of identifier used by artifact assumptions.",
        examples=["md_2026_02_19"],
    )
    fx_as_of: str = Field(
        description="FX snapshot as-of identifier used by artifact assumptions.",
        examples=["md_2026_02_19"],
    )
    valuation_mode: str = Field(
        description="Valuation mode effective for the simulation.",
        examples=["CALCULATED"],
    )


class ProposalArtifactInclusionFlag(BaseModel):
    included: bool = Field(
        description="Whether the component is included in simulation.", examples=[False]
    )
    notes: str = Field(
        description="Deterministic note describing inclusion/exclusion scope.",
        examples=["Transaction costs and bid/ask spread are not modeled."],
    )


class ProposalArtifactAssumptionsAndLimits(BaseModel):
    pricing: ProposalArtifactPricingAssumptions = Field(
        description="Pricing and valuation assumptions."
    )
    costs_and_fees: ProposalArtifactInclusionFlag = Field(
        description="Costs and fees inclusion statement."
    )
    tax: ProposalArtifactInclusionFlag = Field(description="Tax inclusion statement.")
    execution: ProposalArtifactInclusionFlag = Field(description="Execution inclusion statement.")


class ProposalArtifactProductDoc(BaseModel):
    instrument_id: str = Field(description="Instrument identifier.", examples=["US_EQ_ETF"])
    doc_ref: str = Field(
        description="Product-document reference for advisor review.",
        examples=["KID/FactSheet reference pending source confirmation"],
    )


class ProposalArtifactDisclosures(BaseModel):
    risk_disclaimer: str = Field(
        description="Standard deterministic risk disclaimer.",
        examples=[
            "This proposal is based on market-data snapshots and does not guarantee "
            "future performance."
        ],
    )
    product_docs: List[ProposalArtifactProductDoc] = Field(
        default_factory=list,
        description="Product-document references for traded instruments.",
    )
