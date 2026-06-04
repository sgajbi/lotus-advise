from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import ProposalAlternatives
from src.core.advisory.artifact_portfolio_models import (
    ProposalArtifactPortfolioDelta,  # noqa: F401
    ProposalArtifactPortfolioImpact,
    ProposalArtifactPortfolioState,  # noqa: F401
    ProposalArtifactWeightChange,  # noqa: F401
)
from src.core.advisory.artifact_review_models import (
    ProposalArtifactRiskLens,
    ProposalArtifactSuitabilityHighlight,  # noqa: F401
    ProposalArtifactSuitabilitySummary,
)
from src.core.advisory.artifact_summary_models import (
    ProposalArtifactSummary,
    ProposalArtifactSummaryNote,  # noqa: F401
    ProposalArtifactTakeaway,  # noqa: F401
)
from src.core.advisory.artifact_trade_models import (
    ProposalArtifactExecutionNote,  # noqa: F401
    ProposalArtifactFx,  # noqa: F401
    ProposalArtifactTrade,  # noqa: F401
    ProposalArtifactTradeRationale,  # noqa: F401
    ProposalArtifactTradesAndFunding,
)
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.advisory.narrative_models import ProposalNarrative
from src.core.gate_models import GateDecision


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


class ProposalArtifactEvidenceInputs(BaseModel):
    portfolio_snapshot: Dict[str, Any] = Field(
        description="Original portfolio snapshot input payload."
    )
    market_data_snapshot: Dict[str, Any] = Field(
        description="Original market-data snapshot input payload."
    )
    shelf_entries: List[Dict[str, Any]] = Field(description="Original shelf entries input payload.")
    options: Dict[str, Any] = Field(description="Original request options payload.")
    proposed_cash_flows: List[Dict[str, Any]] = Field(
        description="Original proposed cash-flow payload rows."
    )
    proposed_trades: List[Dict[str, Any]] = Field(
        description="Original proposed trade payload rows."
    )
    reference_model: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Original optional reference model payload.",
    )


class ProposalArtifactEngineOutputs(BaseModel):
    proposal_result: Dict[str, Any] = Field(
        description="Full proposal simulation output payload used to build artifact."
    )


class ProposalArtifactHashes(BaseModel):
    request_hash: str = Field(
        description="Canonical request hash from proposal lineage.",
        examples=["sha256:4e2baf..."],
    )
    artifact_hash: str = Field(
        description="Canonical artifact hash excluding volatile fields.",
        examples=["sha256:10ffab..."],
    )


class ProposalArtifactEvidenceBundle(BaseModel):
    inputs: ProposalArtifactEvidenceInputs = Field(description="Input evidence payloads.")
    engine_outputs: ProposalArtifactEngineOutputs = Field(
        description="Engine output evidence payloads."
    )
    hashes: ProposalArtifactHashes = Field(description="Request and artifact hashes.")
    engine_version: str = Field(
        description="Engine version captured in proposal lineage.",
        examples=["0.1.0"],
    )


class ProposalArtifact(BaseModel):
    artifact_id: str = Field(description="Artifact identifier.", examples=["pa_abc12345"])
    proposal_run_id: str = Field(description="Proposal run identifier.", examples=["pr_abc12345"])
    correlation_id: str = Field(description="Correlation identifier.", examples=["corr_123abc"])
    created_at: str = Field(
        description="Artifact creation timestamp in UTC ISO8601.",
        examples=["2026-02-19T12:00:00+00:00"],
    )
    status: Literal["READY", "PENDING_REVIEW", "BLOCKED"] = Field(
        description="Top-level artifact domain status copied from proposal output.",
        examples=["READY"],
    )
    gate_decision: GateDecision = Field(
        description="Deterministic workflow gate decision copied from proposal simulation output."
    )
    proposal_decision_summary: ProposalDecisionSummary | None = Field(
        default=None,
        description=(
            "Backend-owned proposal decision summary copied from proposal simulation output."
        ),
    )
    proposal_alternatives: ProposalAlternatives | None = Field(
        default=None,
        description=(
            "Backend-owned proposal alternatives copied from proposal simulation output when "
            "alternatives are requested or persisted."
        ),
    )
    proposal_narrative: ProposalNarrative | None = Field(
        default=None,
        description=(
            "Optional advisor-review narrative generated from artifact evidence when explicitly "
            "requested. Supports deterministic template mode and opt-in "
            "`AI_ASSISTED_DRAFT`; client-ready narrative remains gated."
        ),
    )
    summary: ProposalArtifactSummary = Field(description="Artifact summary section.")
    portfolio_impact: ProposalArtifactPortfolioImpact = Field(
        description="Before/after allocation and delta section."
    )
    trades_and_funding: ProposalArtifactTradesAndFunding = Field(
        description="Deterministic trade and funding section."
    )
    risk_lens: ProposalArtifactRiskLens = Field(
        description="Concise proposal concentration risk lens section."
    )
    suitability_summary: ProposalArtifactSuitabilitySummary = Field(
        description="Suitability summary section."
    )
    assumptions_and_limits: ProposalArtifactAssumptionsAndLimits = Field(
        description="Assumptions and model limits section."
    )
    disclosures: ProposalArtifactDisclosures = Field(
        description="Disclosure section for advisor review."
    )
    evidence_bundle: ProposalArtifactEvidenceBundle = Field(
        description="Evidence payload section for reproducibility."
    )
