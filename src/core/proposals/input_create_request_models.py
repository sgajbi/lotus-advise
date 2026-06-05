from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.contract_types import ProposalInputMode
from src.core.proposals.input_context_models import (
    ProposalCreateMetadata,
    ProposalStatefulInput,
    ProposalStatelessInput,
)
from src.core.proposals.input_request_validation import validate_exclusive_input_contract


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
        legacy_message = (
            "legacy proposal create requests require simulate_request and must not "
            "include stateless_input or stateful_input"
        )
        validate_exclusive_input_contract(
            input_mode=self.input_mode,
            simulate_request=self.simulate_request,
            stateless_input=self.stateless_input,
            stateful_input=self.stateful_input,
            legacy_message=legacy_message,
            legacy_stateful_message=legacy_message,
            stateless_message=(
                "stateless proposal create requests require stateless_input and must not "
                "include simulate_request or stateful_input"
            ),
            stateful_message=(
                "stateful proposal create requests require stateful_input and must not include "
                "simulate_request or stateless_input"
            ),
        )
        return self
