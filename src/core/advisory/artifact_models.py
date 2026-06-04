from typing import Literal

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import ProposalAlternatives
from src.core.advisory.artifact_assumption_models import (
    ProposalArtifactAssumptionsAndLimits,
    ProposalArtifactDisclosures,
    ProposalArtifactInclusionFlag,  # noqa: F401
    ProposalArtifactPricingAssumptions,  # noqa: F401
    ProposalArtifactProductDoc,  # noqa: F401
)
from src.core.advisory.artifact_evidence_models import (
    ProposalArtifactEngineOutputs,  # noqa: F401
    ProposalArtifactEvidenceBundle,
    ProposalArtifactEvidenceInputs,  # noqa: F401
    ProposalArtifactHashes,  # noqa: F401
)
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
from src.core.advisory.narrative_envelope_models import ProposalNarrative
from src.core.gate_models import GateDecision


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
