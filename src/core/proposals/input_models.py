from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.core.advisory.alternatives_models import ProposalAlternativesRequest
from src.core.advisory.narrative_models import ProposalNarrativeRequest
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.contract_types import ProposalInputMode


class ProposalCreateMetadata(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing proposal title.",
        examples=["2026 client portfolio transition plan"],
    )
    advisor_notes: Optional[str] = Field(
        default=None,
        description="Optional free-text advisor notes captured at proposal creation.",
        examples=["Client asked for controlled equity rotation with cash discipline."],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional proposal jurisdiction code.",
        examples=["SG"],
    )
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier for the proposal context.",
        examples=["mandate_growth_01"],
    )


class ProposalStatelessInput(BaseModel):
    simulate_request: ProposalSimulateRequest = Field(
        description=(
            "Full advisory simulation payload supplied directly by the caller for deterministic "
            "proposal create and replay-safe lifecycle workflows."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )


class ProposalStatefulInput(BaseModel):
    portfolio_id: str = Field(
        description="Canonical Lotus portfolio identifier resolved through upstream services.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    as_of: str = Field(
        description="Business date or timestamp used to resolve the authoritative source context.",
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
    narrative_request: Optional[ProposalNarrativeRequest] = Field(
        default=None,
        description=(
            "Optional advisor-review narrative request applied after authoritative portfolio "
            "context is resolved from Lotus Core. Client-ready publication remains gated."
        ),
    )


class ProposalResolvedContext(BaseModel):
    portfolio_id: str = Field(
        description="Resolved portfolio identifier used by proposal evaluation.",
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


class ProposalSimulationRequest(BaseModel):
    input_mode: Optional[ProposalInputMode] = Field(
        default=None,
        description=(
            "Optional simulation input mode. Omit for legacy direct simulation payloads, or set "
            "explicitly to `stateless`/`stateful` for the normalized simulation contract."
        ),
        examples=["stateful"],
    )
    simulate_request: Optional[ProposalSimulateRequest] = Field(
        default=None,
        description=(
            "Legacy full advisory simulation payload. Prefer `stateless_input` or "
            "`stateful_input` for new simulation callers."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )
    stateless_input: Optional[ProposalStatelessInput] = Field(
        default=None,
        description="Direct advisory payload for normalized stateless simulation requests.",
        examples=[
            {
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                        "base_currency": "USD",
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                }
            }
        ],
    )
    stateful_input: Optional[ProposalStatefulInput] = Field(
        default=None,
        description=(
            "Identifier-based authoritative input payload for normalized stateful simulation "
            "requests."
        ),
        examples=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "as_of": "2026-03-25",
                "mandate_id": "mandate_growth_01",
            }
        ],
    )
    alternatives_request: ProposalAlternativesRequest | None = Field(
        default=None,
        description=(
            "Optional backend-owned alternatives request. On stateful simulation requests this "
            "is merged onto the authoritative resolved simulation payload before evaluation."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_top_level_simulation_payload(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        envelope_keys = {"input_mode", "simulate_request", "stateless_input", "stateful_input"}
        if envelope_keys.intersection(value):
            return value
        return {"simulate_request": value}

    @model_validator(mode="after")
    def validate_input_contract(self) -> "ProposalSimulationRequest":
        if self.input_mode is None:
            if self.simulate_request is None or self.stateless_input is not None:
                raise ValueError(
                    "legacy simulation requests require simulate_request and must not include "
                    "stateless_input"
                )
            if self.stateful_input is not None:
                raise ValueError("legacy simulation requests must not include stateful_input")
            return self
        if self.input_mode == "stateless":
            if (
                self.stateless_input is None
                or self.simulate_request is not None
                or self.stateful_input is not None
            ):
                raise ValueError(
                    "stateless simulation requests require stateless_input and must not include "
                    "simulate_request or stateful_input"
                )
            return self
        if (
            self.stateful_input is None
            or self.simulate_request is not None
            or self.stateless_input is not None
        ):
            raise ValueError(
                "stateful simulation requests require stateful_input and must not include "
                "simulate_request or stateless_input"
            )
        return self


class ProposalCreateRequest(BaseModel):
    created_by: str = Field(
        description="Actor id creating the proposal record.",
        examples=["advisor_123"],
    )
    input_mode: Optional[ProposalInputMode] = Field(
        default=None,
        description=(
            "Optional proposal input mode. Omit for legacy direct `simulate_request` create "
            "requests, or set explicitly to `stateless`/`stateful` for the normalized contract."
        ),
        examples=["stateful"],
    )
    simulate_request: Optional[ProposalSimulateRequest] = Field(
        default=None,
        description=(
            "Legacy full advisory simulation payload persisted as version evidence input. "
            "Prefer `stateless_input` or `stateful_input` for new proposal create callers."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )
    stateless_input: Optional[ProposalStatelessInput] = Field(
        default=None,
        description="Direct advisory payload for normalized stateless proposal create requests.",
    )
    stateful_input: Optional[ProposalStatefulInput] = Field(
        default=None,
        description=(
            "Identifier-based authoritative input payload for normalized stateful proposal create "
            "requests."
        ),
    )
    metadata: ProposalCreateMetadata = Field(
        default_factory=ProposalCreateMetadata,
        description="Optional proposal metadata persisted alongside proposal aggregate.",
        examples=[
            {
                "title": "2026 client portfolio transition plan",
                "advisor_notes": "Client requested medium-risk equity rotation.",
                "jurisdiction": "SG",
                "mandate_id": "mandate_growth_01",
            }
        ],
    )

    @model_validator(mode="after")
    def validate_input_contract(self) -> "ProposalCreateRequest":
        if self.input_mode is None:
            if (
                self.simulate_request is None
                or self.stateless_input is not None
                or self.stateful_input is not None
            ):
                raise ValueError(
                    "legacy proposal create requests require simulate_request and must not "
                    "include stateless_input or stateful_input"
                )
            return self
        if self.input_mode == "stateless":
            if (
                self.stateless_input is None
                or self.simulate_request is not None
                or self.stateful_input is not None
            ):
                raise ValueError(
                    "stateless proposal create requests require stateless_input and must not "
                    "include simulate_request or stateful_input"
                )
            return self
        if (
            self.stateful_input is None
            or self.simulate_request is not None
            or self.stateless_input is not None
        ):
            raise ValueError(
                "stateful proposal create requests require stateful_input and must not include "
                "simulate_request or stateless_input"
            )
        return self


class ProposalVersionRequest(BaseModel):
    created_by: str = Field(
        description="Actor id creating the new proposal version.",
        examples=["advisor_456"],
    )
    expected_current_version_no: Optional[int] = Field(
        default=None,
        description=(
            "Optional optimistic concurrency guard requiring the persisted proposal "
            "to still be at this current version number before creating a new version."
        ),
        examples=[1],
    )
    input_mode: Optional[ProposalInputMode] = Field(
        default=None,
        description=(
            "Optional proposal version input mode. Omit for legacy direct `simulate_request` "
            "version requests, or set explicitly to `stateless`/`stateful` for the normalized "
            "contract."
        ),
        examples=["stateful"],
    )
    simulate_request: Optional[ProposalSimulateRequest] = Field(
        default=None,
        description=(
            "Legacy full advisory simulation payload for the new immutable version. Prefer "
            "`stateless_input` or `stateful_input` for new proposal version callers."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )
    stateless_input: Optional[ProposalStatelessInput] = Field(
        default=None,
        description="Direct advisory payload for normalized stateless proposal version requests.",
    )
    stateful_input: Optional[ProposalStatefulInput] = Field(
        default=None,
        description=(
            "Identifier-based authoritative input payload for normalized stateful proposal "
            "version requests."
        ),
    )

    @model_validator(mode="after")
    def validate_input_contract(self) -> "ProposalVersionRequest":
        if self.input_mode is None:
            if (
                self.simulate_request is None
                or self.stateless_input is not None
                or self.stateful_input is not None
            ):
                raise ValueError(
                    "legacy proposal version requests require simulate_request and must not "
                    "include stateless_input or stateful_input"
                )
            return self
        if self.input_mode == "stateless":
            if (
                self.stateless_input is None
                or self.simulate_request is not None
                or self.stateful_input is not None
            ):
                raise ValueError(
                    "stateless proposal version requests require stateless_input and must not "
                    "include simulate_request or stateful_input"
                )
            return self
        if (
            self.stateful_input is None
            or self.simulate_request is not None
            or self.stateless_input is not None
        ):
            raise ValueError(
                "stateful proposal version requests require stateful_input and must not include "
                "simulate_request or stateless_input"
            )
        return self
