from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

ReadinessStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED", "NOT_AVAILABLE"]

_CONTRACT_VERSION = "rfc0024.memo-source-readiness.v1"
_OPEN_END_VALUES = {"3999-12-31", "31-Dec-3999", "31-DEC-3999"}


def build_memo_source_readiness(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    """Build the RFC-0024 source-authority manifest for future memo sections.

    This is not memo generation. It is a deterministic readiness projection over
    already persisted proposal evidence so future memo builders cannot claim a
    source fact that the owning service did not provide.
    """

    context_resolution = _dict_at(evidence_bundle, "context_resolution")
    inputs = _dict_at(evidence_bundle, "inputs")
    engine_outputs = _dict_at(evidence_bundle, "engine_outputs")
    proposal_result = _dict_at(engine_outputs, "proposal_result")
    risk_lens = _dict_at(evidence_bundle, "risk_lens")
    advisory_policy_context = _dict_at(context_resolution, "advisory_policy_context")
    resolution_source = str(context_resolution.get("resolution_source") or "")

    portfolio_snapshot = _dict_at(inputs, "portfolio_snapshot")
    market_data_snapshot = _dict_at(inputs, "market_data_snapshot")
    shelf_entries = _list_at(inputs, "shelf_entries")
    proposed_trades = _list_at(inputs, "proposed_trades")
    proposed_cash_flows = _list_at(inputs, "proposed_cash_flows")
    prices = _list_at(market_data_snapshot, "prices")
    fx_rates = _list_at(market_data_snapshot, "fx_rates")

    sections = [
        _section(
            key="core_portfolio_holdings_cash",
            owner_service="lotus-core",
            status=_core_holdings_cash_status(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
            ),
            evidence_refs=[
                "context_resolution.resolved_context.portfolio_snapshot_id",
                "inputs.portfolio_snapshot.positions",
                "inputs.portfolio_snapshot.cash_balances",
            ],
            missing_evidence=_missing_core_holdings_cash(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
            ),
            reason_codes=_core_holdings_cash_reasons(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
            ),
        ),
        _section(
            key="core_household_account_mandate_objective_restrictions",
            owner_service="lotus-core",
            status=_client_context_status(advisory_policy_context),
            evidence_refs=[
                "context_resolution.advisory_policy_context.household_id",
                "context_resolution.advisory_policy_context.mandate_id",
                "context_resolution.resolved_context",
            ],
            missing_evidence=_missing_client_context(advisory_policy_context),
            reason_codes=_client_context_reasons(advisory_policy_context),
        ),
        _section(
            key="core_market_prices",
            owner_service="lotus-core",
            status=_market_data_status(
                rows=prices,
                resolution_source=resolution_source,
                source_name="price",
            ),
            evidence_refs=[
                "context_resolution.resolved_context.market_data_snapshot_id",
                "inputs.market_data_snapshot.prices",
            ],
            missing_evidence=_market_data_missing(rows=prices, source_name="price"),
            reason_codes=_market_data_reasons(
                rows=prices,
                resolution_source=resolution_source,
                source_name="PRICE",
            ),
        ),
        _section(
            key="core_fx_rates",
            owner_service="lotus-core",
            status=_market_data_status(
                rows=fx_rates,
                resolution_source=resolution_source,
                source_name="FX rate",
            ),
            evidence_refs=[
                "context_resolution.resolved_context.market_data_snapshot_id",
                "inputs.market_data_snapshot.fx_rates",
            ],
            missing_evidence=_market_data_missing(rows=fx_rates, source_name="FX rate"),
            reason_codes=_market_data_reasons(
                rows=fx_rates,
                resolution_source=resolution_source,
                source_name="FX_RATE",
            ),
        ),
        _section(
            key="core_product_eligibility_complexity",
            owner_service="lotus-core",
            status=_product_source_status(
                shelf_entries=shelf_entries,
                proposed_trades=proposed_trades,
            ),
            evidence_refs=[
                "inputs.shelf_entries",
                "inputs.proposed_trades",
            ],
            missing_evidence=_product_source_missing(
                shelf_entries=shelf_entries,
                proposed_trades=proposed_trades,
            ),
            reason_codes=_product_source_reasons(
                shelf_entries=shelf_entries,
                proposed_trades=proposed_trades,
            ),
        ),
        _section(
            key="risk_concentration",
            owner_service="lotus-risk",
            status=_risk_concentration_status(risk_lens),
            evidence_refs=[
                "risk_lens.single_position_concentration",
                "risk_lens.issuer_concentration",
            ],
            missing_evidence=_risk_concentration_missing(risk_lens),
            reason_codes=_risk_concentration_reasons(risk_lens),
        ),
        _section(
            key="risk_drawdown_stress_liquidity_private_assets_climate_geopolitical",
            owner_service="lotus-risk",
            status="PENDING_REVIEW",
            evidence_refs=["risk_lens"],
            missing_evidence=[
                "drawdown",
                "stress",
                "liquidity",
                "private_asset_exposure",
                "climate_geopolitical_exposure",
            ],
            reason_codes=["RISK_OWNER_EXTENDED_MEMO_EVIDENCE_NOT_PROVIDED"],
        ),
        _section(
            key="advise_decision_summary",
            owner_service="lotus-advise",
            status=(
                "READY"
                if isinstance(proposal_result.get("proposal_decision_summary"), dict)
                else "PENDING_REVIEW"
            ),
            evidence_refs=["engine_outputs.proposal_result.proposal_decision_summary"],
            missing_evidence=(
                []
                if isinstance(proposal_result.get("proposal_decision_summary"), dict)
                else ["proposal_decision_summary"]
            ),
            reason_codes=(
                []
                if isinstance(proposal_result.get("proposal_decision_summary"), dict)
                else ["ADVISE_DECISION_SUMMARY_NOT_CAPTURED"]
            ),
        ),
        _section(
            key="advise_alternatives_lifecycle_execution_boundary",
            owner_service="lotus-advise",
            status=_advise_boundary_status(
                proposal_result=proposal_result,
                proposed_trades=proposed_trades,
                proposed_cash_flows=proposed_cash_flows,
            ),
            evidence_refs=[
                "engine_outputs.proposal_result.proposal_alternatives",
                "engine_outputs.proposal_result.gate_decision",
                "inputs.proposed_trades",
                "inputs.proposed_cash_flows",
            ],
            missing_evidence=_advise_boundary_missing(proposal_result),
            reason_codes=_advise_boundary_reasons(proposal_result),
        ),
    ]

    return {
        "contract_version": _CONTRACT_VERSION,
        "capability_posture": "SOURCE_READINESS_ONLY_MEMO_GENERATION_NOT_IMPLEMENTED",
        "overall_posture": _overall_posture(sections),
        "source_authority": _source_authority(sections),
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


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_at(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _section(
    *,
    key: str,
    owner_service: str,
    status: ReadinessStatus,
    evidence_refs: list[str],
    missing_evidence: list[str],
    reason_codes: list[str],
) -> dict[str, Any]:
    return {
        "key": key,
        "owner_service": owner_service,
        "status": status,
        "evidence_refs": evidence_refs,
        "missing_evidence": missing_evidence,
        "reason_codes": reason_codes,
    }


def _core_holdings_cash_status(
    *, resolution_source: str, portfolio_snapshot: dict[str, Any]
) -> ReadinessStatus:
    if not _list_at(portfolio_snapshot, "positions") or not _list_at(
        portfolio_snapshot, "cash_balances"
    ):
        return "BLOCKED"
    return "READY" if resolution_source == "LOTUS_CORE" else "PENDING_REVIEW"


def _missing_core_holdings_cash(
    *, resolution_source: str, portfolio_snapshot: dict[str, Any]
) -> list[str]:
    missing = []
    if resolution_source != "LOTUS_CORE":
        missing.append("lotus-core authoritative context resolution")
    if not _list_at(portfolio_snapshot, "positions"):
        missing.append("positions")
    if not _list_at(portfolio_snapshot, "cash_balances"):
        missing.append("cash_balances")
    return missing


def _core_holdings_cash_reasons(
    *, resolution_source: str, portfolio_snapshot: dict[str, Any]
) -> list[str]:
    reasons = []
    if resolution_source != "LOTUS_CORE":
        reasons.append("DIRECT_REQUEST_NOT_SOURCE_OWNER")
    if not _list_at(portfolio_snapshot, "positions"):
        reasons.append("CORE_POSITIONS_NOT_PROVIDED")
    if not _list_at(portfolio_snapshot, "cash_balances"):
        reasons.append("CORE_CASH_NOT_PROVIDED")
    return reasons


def _client_context_status(policy_context: dict[str, Any]) -> ReadinessStatus:
    missing = _missing_client_context(policy_context)
    if not missing:
        return "READY"
    return "BLOCKED" if {"household_id", "mandate_id"}.issubset(set(missing)) else "PENDING_REVIEW"


def _missing_client_context(policy_context: dict[str, Any]) -> list[str]:
    missing = []
    if not policy_context.get("household_id"):
        missing.append("household_id")
    if not policy_context.get("mandate_id"):
        missing.append("mandate_id")
    missing.extend(["account_id", "objectives", "restrictions"])
    return missing


def _client_context_reasons(policy_context: dict[str, Any]) -> list[str]:
    reasons = []
    if not policy_context.get("household_id"):
        reasons.append("CORE_HOUSEHOLD_NOT_PROVIDED")
    if not policy_context.get("mandate_id"):
        reasons.append("CORE_MANDATE_NOT_PROVIDED")
    reasons.extend(
        [
            "CORE_ACCOUNT_NOT_PROVIDED",
            "CORE_OBJECTIVES_NOT_PROVIDED",
            "CORE_RESTRICTIONS_NOT_PROVIDED",
        ]
    )
    return reasons


def _market_data_status(
    *, rows: list[Any], resolution_source: str, source_name: str
) -> ReadinessStatus:
    if not rows:
        return "BLOCKED" if source_name == "price" else "PENDING_REVIEW"
    if resolution_source != "LOTUS_CORE" or not _all_rows_open_ended(rows):
        return "PENDING_REVIEW"
    return "READY"


def _market_data_missing(*, rows: list[Any], source_name: str) -> list[str]:
    if not rows:
        return [f"{source_name} rows"]
    missing = []
    if not _all_rows_open_ended(rows):
        missing.append(f"{source_name} validity end 31-Dec-3999")
    return missing


def _market_data_reasons(*, rows: list[Any], resolution_source: str, source_name: str) -> list[str]:
    reasons = []
    if not rows:
        reasons.append(f"CORE_{source_name}_NOT_PROVIDED")
    if rows and not _all_rows_open_ended(rows):
        reasons.append(f"CORE_{source_name}_OPEN_END_DATE_NOT_PROVIDED")
    if resolution_source != "LOTUS_CORE":
        reasons.append("DIRECT_REQUEST_NOT_SOURCE_OWNER")
    return reasons


def _all_rows_open_ended(rows: list[Any]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            return False
        values = {
            str(row.get(key) or "")
            for key in (
                "valid_to",
                "validTo",
                "effective_to",
                "effectiveTo",
                "end_date",
                "endDate",
                "open_until",
                "openUntil",
            )
        }
        if not values.intersection(_OPEN_END_VALUES):
            return False
    return True


def _product_source_status(
    *, shelf_entries: list[Any], proposed_trades: list[Any]
) -> ReadinessStatus:
    if not proposed_trades:
        return "NOT_AVAILABLE"
    if not shelf_entries:
        return "BLOCKED"
    if _all_products_have_eligibility_and_complexity(shelf_entries):
        return "READY"
    return "PENDING_REVIEW"


def _product_source_missing(*, shelf_entries: list[Any], proposed_trades: list[Any]) -> list[str]:
    if not proposed_trades:
        return []
    if not shelf_entries:
        return ["shelf_entries"]
    if _all_products_have_eligibility_and_complexity(shelf_entries):
        return []
    return ["product_eligibility", "product_complexity"]


def _product_source_reasons(*, shelf_entries: list[Any], proposed_trades: list[Any]) -> list[str]:
    if not proposed_trades:
        return []
    if not shelf_entries:
        return ["CORE_PRODUCT_SHELF_NOT_PROVIDED"]
    if _all_products_have_eligibility_and_complexity(shelf_entries):
        return []
    return ["CORE_PRODUCT_ELIGIBILITY_OR_COMPLEXITY_NOT_PROVIDED"]


def _all_products_have_eligibility_and_complexity(rows: list[Any]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            return False
        raw_attributes = row.get("attributes")
        attributes: dict[str, Any] = raw_attributes if isinstance(raw_attributes, dict) else {}
        has_eligibility = bool(row.get("eligibility") or attributes.get("eligibility"))
        has_complexity = bool(
            row.get("complexity")
            or row.get("product_complexity")
            or attributes.get("complexity")
            or attributes.get("product_complexity")
        )
        if not has_eligibility or not has_complexity:
            return False
    return True


def _risk_concentration_status(risk_lens: dict[str, Any]) -> ReadinessStatus:
    if risk_lens.get("source_service") != "lotus-risk":
        return "PENDING_REVIEW"
    if isinstance(risk_lens.get("single_position_concentration"), dict) and isinstance(
        risk_lens.get("issuer_concentration"), dict
    ):
        return "READY"
    return "PENDING_REVIEW"


def _risk_concentration_missing(risk_lens: dict[str, Any]) -> list[str]:
    missing = []
    if risk_lens.get("source_service") != "lotus-risk":
        missing.append("lotus-risk source_service")
    if not isinstance(risk_lens.get("single_position_concentration"), dict):
        missing.append("single_position_concentration")
    if not isinstance(risk_lens.get("issuer_concentration"), dict):
        missing.append("issuer_concentration")
    return missing


def _risk_concentration_reasons(risk_lens: dict[str, Any]) -> list[str]:
    if not _risk_concentration_missing(risk_lens):
        return []
    return ["RISK_CONCENTRATION_SOURCE_EVIDENCE_INCOMPLETE"]


def _advise_boundary_status(
    *,
    proposal_result: dict[str, Any],
    proposed_trades: list[Any],
    proposed_cash_flows: list[Any],
) -> ReadinessStatus:
    has_gate = isinstance(proposal_result.get("gate_decision"), dict)
    has_activity = bool(proposed_trades or proposed_cash_flows)
    has_alternatives = isinstance(proposal_result.get("proposal_alternatives"), dict)
    if has_gate and (has_alternatives or has_activity):
        return "READY"
    return "PENDING_REVIEW"


def _advise_boundary_missing(proposal_result: dict[str, Any]) -> list[str]:
    missing = []
    if not isinstance(proposal_result.get("gate_decision"), dict):
        missing.append("gate_decision")
    if not isinstance(proposal_result.get("proposal_alternatives"), dict):
        missing.append("proposal_alternatives")
    return missing


def _advise_boundary_reasons(proposal_result: dict[str, Any]) -> list[str]:
    missing = _advise_boundary_missing(proposal_result)
    if not missing:
        return []
    return [f"ADVISE_{item.upper()}_NOT_CAPTURED" for item in missing]


def _overall_posture(sections: list[dict[str, Any]]) -> ReadinessStatus:
    statuses = {section["status"] for section in sections}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "PENDING_REVIEW" in statuses:
        return "PENDING_REVIEW"
    if "READY" in statuses:
        return "READY"
    return "NOT_AVAILABLE"


def _source_authority(sections: list[dict[str, Any]]) -> dict[str, Any]:
    authority: dict[str, Any] = {}
    for section in sections:
        owner = section["owner_service"]
        authority.setdefault(owner, {"section_keys": [], "ready_section_keys": []})
        authority[owner]["section_keys"].append(section["key"])
        if section["status"] == "READY":
            authority[owner]["ready_section_keys"].append(section["key"])
    return authority
