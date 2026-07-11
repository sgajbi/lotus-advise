from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.source_provenance_models import SourceProvenanceEnvelope

WorkspaceInputMode = Literal["stateless", "stateful"]


class WorkspaceStatelessInput(BaseModel):
    simulate_request: ProposalSimulateRequest = Field(
        description=(
            "Full advisory simulation payload supplied directly by the caller for sandbox, replay, "
            "or external integration workflows."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "250000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )


class WorkspaceStatefulInput(BaseModel):
    portfolio_id: str = Field(
        description="Canonical Lotus portfolio identifier resolved through upstream services.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of: str = Field(
        description="Business date or timestamp used to resolve the source portfolio context.",
        examples=["2026-03-25"],
    )
    household_id: Optional[str] = Field(
        default=None,
        description="Optional household identifier when the advisory workflow is household-scoped.",
        examples=["hh_001"],
    )
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier used to enrich the advisory context.",
        examples=["mandate_growth_01"],
    )
    benchmark_id: Optional[str] = Field(
        default=None,
        description="Optional benchmark identifier for context-aware evaluation and comparison.",
        examples=["benchmark_balanced_usd"],
    )


class WorkspaceResolvedContext(BaseModel):
    portfolio_id: str = Field(
        description="Resolved portfolio identifier used by the workspace evaluation.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of: str = Field(
        description="Resolved business date or timestamp used during evaluation.",
        examples=["2026-03-25"],
    )
    portfolio_snapshot_id: Optional[str] = Field(
        default=None,
        description="Upstream portfolio snapshot identifier captured for replay and audit.",
        examples=["ps_20260325_001"],
    )
    market_data_snapshot_id: Optional[str] = Field(
        default=None,
        description="Upstream market-data snapshot identifier captured for replay and audit.",
        examples=["md_20260325_001"],
    )
    risk_context_id: Optional[str] = Field(
        default=None,
        description="Optional upstream risk-context identifier used for advisory enrichment.",
        examples=["risk_ctx_001"],
    )
    reporting_context_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional reporting-context identifier used to correlate downstream report generation."
        ),
        examples=["report_ctx_001"],
    )
    source_provenance: Optional[SourceProvenanceEnvelope] = Field(
        default=None,
        description=(
            "Optional upstream source snapshot, version, freshness, and contract evidence used "
            "to resolve this workspace context."
        ),
    )
