from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.core.advisory.alternatives_models import ProposalAlternativesRequest
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.contract_types import ProposalInputMode
from src.core.proposals.input_context_models import (
    ProposalCreateMetadata,
    ProposalStatefulInput,
    ProposalStatelessInput,
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
