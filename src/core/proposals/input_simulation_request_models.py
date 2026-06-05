from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.core.advisory.alternatives_models import ProposalAlternativesRequest
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.contract_types import ProposalInputMode
from src.core.proposals.input_context_models import (
    ProposalStatefulInput,
    ProposalStatelessInput,
)
from src.core.proposals.input_request_validation import validate_exclusive_input_contract


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
        validate_exclusive_input_contract(
            input_mode=self.input_mode,
            simulate_request=self.simulate_request,
            stateless_input=self.stateless_input,
            stateful_input=self.stateful_input,
            legacy_message=(
                "legacy simulation requests require simulate_request and must not include "
                "stateless_input"
            ),
            legacy_stateful_message="legacy simulation requests must not include stateful_input",
            stateless_message=(
                "stateless simulation requests require stateless_input and must not include "
                "simulate_request or stateful_input"
            ),
            stateful_message=(
                "stateful simulation requests require stateful_input and must not include "
                "simulate_request or stateless_input"
            ),
        )
        return self
