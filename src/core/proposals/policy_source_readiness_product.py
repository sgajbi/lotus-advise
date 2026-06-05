from __future__ import annotations

from typing import Any, cast

from src.core.proposals.source_readiness_common import ReadinessStatus, source_readiness_section


def build_product_policy_source_section(
    *, proposed_trades: list[Any], shelf_entries: list[Any]
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
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
    )


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
        if not _product_has_policy_evidence(row):
            return False
    return True


def _product_has_policy_evidence(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    attributes = _attributes(row)
    return (
        _has_policy_value(row, attributes, "eligibility")
        and _has_policy_value(row, attributes, "target_market")
        and _has_any_policy_value(row, attributes, ("complexity", "product_complexity"))
        and _has_any_policy_key(
            row,
            attributes,
            (
                "private_asset",
                "private_asset_flag",
                "structured_product",
                "structured_product_flag",
            ),
        )
    )


def _attributes(row: dict[str, Any]) -> dict[str, Any]:
    raw_attributes = row.get("attributes")
    return raw_attributes if isinstance(raw_attributes, dict) else {}


def _has_policy_value(row: dict[str, Any], attributes: dict[str, Any], key: str) -> bool:
    return bool(row.get(key) or attributes.get(key))


def _has_any_policy_value(
    row: dict[str, Any],
    attributes: dict[str, Any],
    keys: tuple[str, ...],
) -> bool:
    return any(_has_policy_value(row, attributes, key) for key in keys)


def _has_any_policy_key(
    row: dict[str, Any],
    attributes: dict[str, Any],
    keys: tuple[str, ...],
) -> bool:
    return any(key in row or key in attributes for key in keys)
