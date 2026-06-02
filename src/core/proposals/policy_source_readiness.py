from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.proposals.policy_source_readiness_core import build_core_policy_source_sections
from src.core.proposals.policy_source_readiness_product import build_product_policy_source_section
from src.core.proposals.policy_source_readiness_risk import build_risk_policy_source_section
from src.core.proposals.source_readiness_common import (
    dict_at,
    list_at,
    overall_posture,
    source_authority,
    source_readiness_section,
)

_CONTRACT_VERSION = "rfc0025.policy-source-readiness.v1"


def build_policy_source_readiness(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    """Project source-owner readiness for future RFC-0025 policy evaluation.

    This is not policy evaluation. It is a deterministic source-evidence manifest over
    already captured proposal evidence so future policy-pack work cannot claim suitability,
    best-interest, eligibility, disclosure, or consent facts that source owners did not provide.
    """

    context_resolution = dict_at(evidence_bundle, "context_resolution")
    inputs = dict_at(evidence_bundle, "inputs")
    risk_lens = dict_at(evidence_bundle, "risk_lens")
    advisory_policy_context = dict_at(context_resolution, "advisory_policy_context")
    resolution_source = str(context_resolution.get("resolution_source") or "")

    portfolio_snapshot = dict_at(inputs, "portfolio_snapshot")
    market_data_snapshot = dict_at(inputs, "market_data_snapshot")
    proposed_trades = list_at(inputs, "proposed_trades")
    shelf_entries = list_at(inputs, "shelf_entries")
    prices = list_at(market_data_snapshot, "prices")
    fx_rates = list_at(market_data_snapshot, "fx_rates")

    sections = [
        *build_core_policy_source_sections(
            advisory_policy_context=advisory_policy_context,
            resolution_source=resolution_source,
            portfolio_snapshot=portfolio_snapshot,
            prices=prices,
            fx_rates=fx_rates,
        ),
        build_product_policy_source_section(
            proposed_trades=proposed_trades,
            shelf_entries=shelf_entries,
        ),
        build_risk_policy_source_section(risk_lens),
        source_readiness_section(
            key="advise_policy_evaluation_runtime",
            owner_service="lotus-advise",
            status="READY",
            evidence_refs=[
                "evidence_bundle.policy_source_readiness",
                "contracts.domain-data-products.AdvisoryPolicyEvaluationRecord",
            ],
            missing_evidence=[],
            reason_codes=["RFC0025_INTERNAL_POLICY_EVALUATION_ENGINE_AVAILABLE"],
        ),
    ]

    return {
        "contract_version": _CONTRACT_VERSION,
        "capability_posture": "SOURCE_READINESS_WITH_INTERNAL_POLICY_EVALUATION_ENGINE",
        "overall_posture": overall_posture(sections),
        "source_authority": source_authority(sections),
        "sections": deepcopy(sections),
        "claim_policy": {
            "policy_evaluation": "INTERNAL_ENGINE_ONLY_NO_PERSISTED_API",
            "client_ready_publication": "BLOCKED",
            "unsupported_fact_handling": (
                "Do not claim policy suitability, best-interest, eligibility, disclosure, "
                "consent, or approval facts without READY source-owner evidence; carry "
                "PENDING_REVIEW or BLOCKED posture instead."
            ),
        },
    }
