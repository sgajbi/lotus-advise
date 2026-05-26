from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.proposals.source_readiness_common import (
    ReadinessStatus,
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
        source_readiness_section(
            key="core_client_profile_classification",
            owner_service="lotus-core",
            status=_client_profile_status(advisory_policy_context),
            evidence_refs=[
                "context_resolution.advisory_policy_context.household_id",
                "context_resolution.advisory_policy_context.jurisdiction",
                "context_resolution.resolved_context",
            ],
            missing_evidence=_client_profile_missing(advisory_policy_context),
            reason_codes=_client_profile_reasons(advisory_policy_context),
        ),
        source_readiness_section(
            key="core_mandate_objectives_restrictions",
            owner_service="lotus-core",
            status=_mandate_status(advisory_policy_context),
            evidence_refs=[
                "context_resolution.advisory_policy_context.mandate_id",
                "context_resolution.resolved_context",
            ],
            missing_evidence=_mandate_missing(advisory_policy_context),
            reason_codes=_mandate_reasons(advisory_policy_context),
        ),
        source_readiness_section(
            key="core_holdings_cash_market_data",
            owner_service="lotus-core",
            status=_holdings_market_status(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
                prices=prices,
                fx_rates=fx_rates,
            ),
            evidence_refs=[
                "inputs.portfolio_snapshot.positions",
                "inputs.portfolio_snapshot.cash_balances",
                "inputs.market_data_snapshot.prices",
                "inputs.market_data_snapshot.fx_rates",
            ],
            missing_evidence=_holdings_market_missing(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
                prices=prices,
                fx_rates=fx_rates,
            ),
            reason_codes=_holdings_market_reasons(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
                prices=prices,
                fx_rates=fx_rates,
            ),
        ),
        source_readiness_section(
            key="core_product_eligibility_target_market_complexity",
            owner_service="lotus-core",
            status=_product_policy_status(
                proposed_trades=proposed_trades,
                shelf_entries=shelf_entries,
            ),
            evidence_refs=[
                "inputs.proposed_trades",
                "inputs.shelf_entries",
            ],
            missing_evidence=_product_policy_missing(
                proposed_trades=proposed_trades,
                shelf_entries=shelf_entries,
            ),
            reason_codes=_product_policy_reasons(
                proposed_trades=proposed_trades,
                shelf_entries=shelf_entries,
            ),
        ),
        source_readiness_section(
            key="risk_policy_metrics",
            owner_service="lotus-risk",
            status=_risk_policy_status(risk_lens),
            evidence_refs=[
                "risk_lens.single_position_concentration",
                "risk_lens.issuer_concentration",
                "risk_lens.drawdown",
                "risk_lens.var",
                "risk_lens.stress",
                "risk_lens.liquidity_risk",
                "risk_lens.private_asset_risk",
                "risk_lens.climate_geopolitical_risk",
            ],
            missing_evidence=_risk_policy_missing(risk_lens),
            reason_codes=_risk_policy_reasons(risk_lens),
        ),
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


def _client_profile_status(policy_context: dict[str, Any]) -> ReadinessStatus:
    missing = _client_profile_missing(policy_context)
    if not missing:
        return "READY"
    required = {"household_id", "jurisdiction"}
    return "BLOCKED" if required.issubset(set(missing)) else "PENDING_REVIEW"


def _client_profile_missing(policy_context: dict[str, Any]) -> list[str]:
    missing = []
    for key in (
        "household_id",
        "jurisdiction",
        "client_classification",
        "booking_center_code",
        "account_id",
        "time_horizon",
        "liquidity_need",
    ):
        if not policy_context.get(key):
            missing.append(key)
    return missing


def _client_profile_reasons(policy_context: dict[str, Any]) -> list[str]:
    return [f"CORE_{key.upper()}_NOT_PROVIDED" for key in _client_profile_missing(policy_context)]


def _mandate_status(policy_context: dict[str, Any]) -> ReadinessStatus:
    missing = _mandate_missing(policy_context)
    if not missing:
        return "READY"
    return "BLOCKED" if "mandate_id" in missing else "PENDING_REVIEW"


def _mandate_missing(policy_context: dict[str, Any]) -> list[str]:
    missing = []
    for key in ("mandate_id", "objectives", "restrictions"):
        if not policy_context.get(key):
            missing.append(key)
    return missing


def _mandate_reasons(policy_context: dict[str, Any]) -> list[str]:
    return [f"CORE_{key.upper()}_NOT_PROVIDED" for key in _mandate_missing(policy_context)]


def _holdings_market_status(
    *,
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> ReadinessStatus:
    missing = _holdings_market_missing(
        resolution_source=resolution_source,
        portfolio_snapshot=portfolio_snapshot,
        prices=prices,
        fx_rates=fx_rates,
    )
    blocking = {"positions", "price rows"}
    if blocking.intersection(missing):
        return "BLOCKED"
    return "READY" if not missing else "PENDING_REVIEW"


def _holdings_market_missing(
    *,
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> list[str]:
    missing = []
    if resolution_source != "LOTUS_CORE":
        missing.append("lotus-core authoritative context resolution")
    if not list_at(portfolio_snapshot, "positions"):
        missing.append("positions")
    if not list_at(portfolio_snapshot, "cash_balances"):
        missing.append("cash_balances")
    if not prices:
        missing.append("price rows")
    if not fx_rates:
        missing.append("FX rate rows")
    return missing


def _holdings_market_reasons(
    *,
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> list[str]:
    reasons = []
    if resolution_source != "LOTUS_CORE":
        reasons.append("DIRECT_REQUEST_NOT_SOURCE_OWNER")
    if not list_at(portfolio_snapshot, "positions"):
        reasons.append("CORE_POSITIONS_NOT_PROVIDED")
    if not list_at(portfolio_snapshot, "cash_balances"):
        reasons.append("CORE_CASH_NOT_PROVIDED")
    if not prices:
        reasons.append("CORE_PRICE_NOT_PROVIDED")
    if not fx_rates:
        reasons.append("CORE_FX_RATE_NOT_PROVIDED")
    return reasons


def _product_policy_status(
    *, proposed_trades: list[Any], shelf_entries: list[Any]
) -> ReadinessStatus:
    if not proposed_trades:
        return "NOT_AVAILABLE"
    if not shelf_entries:
        return "BLOCKED"
    return "READY" if _all_products_have_policy_evidence(shelf_entries) else "PENDING_REVIEW"


def _product_policy_missing(*, proposed_trades: list[Any], shelf_entries: list[Any]) -> list[str]:
    if not proposed_trades:
        return []
    if not shelf_entries:
        return ["shelf_entries"]
    if _all_products_have_policy_evidence(shelf_entries):
        return []
    return [
        "product_eligibility",
        "target_market",
        "product_complexity",
        "private_asset_or_structured_product_flag",
    ]


def _product_policy_reasons(*, proposed_trades: list[Any], shelf_entries: list[Any]) -> list[str]:
    if not proposed_trades:
        return []
    if not shelf_entries:
        return ["CORE_PRODUCT_SHELF_NOT_PROVIDED"]
    if _all_products_have_policy_evidence(shelf_entries):
        return []
    return ["CORE_PRODUCT_POLICY_EVIDENCE_INCOMPLETE"]


def _all_products_have_policy_evidence(rows: list[Any]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            return False
        raw_attributes = row.get("attributes")
        attributes: dict[str, Any] = raw_attributes if isinstance(raw_attributes, dict) else {}
        has_eligibility = bool(row.get("eligibility") or attributes.get("eligibility"))
        has_target_market = bool(row.get("target_market") or attributes.get("target_market"))
        has_complexity = bool(
            row.get("complexity")
            or row.get("product_complexity")
            or attributes.get("complexity")
            or attributes.get("product_complexity")
        )
        has_product_flags = any(
            key in row or key in attributes
            for key in (
                "private_asset",
                "private_asset_flag",
                "structured_product",
                "structured_product_flag",
            )
        )
        if not (has_eligibility and has_target_market and has_complexity and has_product_flags):
            return False
    return True


def _risk_policy_status(risk_lens: dict[str, Any]) -> ReadinessStatus:
    if risk_lens.get("source_service") != "lotus-risk":
        return "BLOCKED"
    if _risk_policy_degraded(risk_lens):
        return "PENDING_REVIEW"
    return "READY" if not _risk_policy_missing(risk_lens) else "PENDING_REVIEW"


def _risk_policy_missing(risk_lens: dict[str, Any]) -> list[str]:
    missing = []
    if risk_lens.get("source_service") != "lotus-risk":
        missing.append("lotus-risk source_service")
    if _risk_policy_degraded(risk_lens):
        missing.append("lotus-risk degraded policy metrics")
    for key in (
        "single_position_concentration",
        "issuer_concentration",
        "drawdown",
        "var",
        "stress",
        "liquidity_risk",
        "private_asset_risk",
        "climate_geopolitical_risk",
    ):
        if not isinstance(risk_lens.get(key), dict):
            missing.append(key)
    return missing


def _risk_policy_reasons(risk_lens: dict[str, Any]) -> list[str]:
    missing = _risk_policy_missing(risk_lens)
    if not missing:
        return []
    if "lotus-risk source_service" in missing:
        return ["RISK_OWNER_POLICY_EVIDENCE_NOT_AVAILABLE"]
    if "lotus-risk degraded policy metrics" in missing:
        return ["RISK_OWNER_POLICY_EVIDENCE_DEGRADED"]
    return ["RISK_OWNER_POLICY_EVIDENCE_INCOMPLETE"]


def _risk_policy_degraded(risk_lens: dict[str, Any]) -> bool:
    supportability = dict_at(risk_lens, "supportability")
    state = str(
        risk_lens.get("supportability_state")
        or risk_lens.get("state")
        or supportability.get("state")
        or supportability.get("status")
        or ""
    ).upper()
    return state in {"DEGRADED", "STALE", "PARTIAL"}
