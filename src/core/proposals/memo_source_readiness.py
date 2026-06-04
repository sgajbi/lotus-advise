from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.proposals.memo_source_readiness_advise import build_advise_memo_source_sections
from src.core.proposals.memo_source_readiness_core import build_core_memo_source_sections
from src.core.proposals.memo_source_readiness_risk import build_risk_memo_source_sections
from src.core.proposals.source_readiness_common import (
    dict_at,
    list_at,
    overall_posture,
    source_authority,
)

_CONTRACT_VERSION = "rfc0024.memo-source-readiness.v1"


def build_memo_source_readiness(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    """Build the RFC-0024 source-authority manifest for future memo sections.

    This is not memo generation. It is a deterministic readiness projection over
    already persisted proposal evidence so future memo builders cannot claim a
    source fact that the owning service did not provide.
    """

    context_resolution = dict_at(evidence_bundle, "context_resolution")
    inputs = dict_at(evidence_bundle, "inputs")
    engine_outputs = dict_at(evidence_bundle, "engine_outputs")
    proposal_result = dict_at(engine_outputs, "proposal_result")
    risk_lens = dict_at(evidence_bundle, "risk_lens")
    advisory_policy_context = dict_at(context_resolution, "advisory_policy_context")
    resolution_source = str(context_resolution.get("resolution_source") or "")

    portfolio_snapshot = dict_at(inputs, "portfolio_snapshot")
    market_data_snapshot = dict_at(inputs, "market_data_snapshot")
    shelf_entries = list_at(inputs, "shelf_entries")
    proposed_trades = list_at(inputs, "proposed_trades")
    proposed_cash_flows = list_at(inputs, "proposed_cash_flows")
    prices = list_at(market_data_snapshot, "prices")
    fx_rates = list_at(market_data_snapshot, "fx_rates")

    sections = [
        *build_core_memo_source_sections(
            resolution_source=resolution_source,
            advisory_policy_context=advisory_policy_context,
            portfolio_snapshot=portfolio_snapshot,
            prices=prices,
            fx_rates=fx_rates,
            shelf_entries=shelf_entries,
            proposed_trades=proposed_trades,
        ),
        *build_risk_memo_source_sections(risk_lens),
        *build_advise_memo_source_sections(
            proposal_result=proposal_result,
            proposed_trades=proposed_trades,
            proposed_cash_flows=proposed_cash_flows,
        ),
    ]

    return {
        "contract_version": _CONTRACT_VERSION,
        "capability_posture": "SOURCE_READINESS_ONLY_MEMO_GENERATION_NOT_IMPLEMENTED",
        "overall_posture": overall_posture(sections),
        "source_authority": source_authority(sections),
        "sections": deepcopy(sections),
        "claim_policy": {
            "memo_generation": "NOT_IMPLEMENTED",
            "client_ready_publication": "BLOCKED",
            "unsupported_fact_handling": (
                "Do not render memo facts without READY source-owner evidence; render "
                "PENDING_REVIEW or BLOCKED posture instead."
            ),
        },
    }
