from __future__ import annotations

from typing import Any, cast

from src.core.proposals.source_readiness_common import dict_at, list_at

_COMPLEX_PRODUCT_CLASSIFICATIONS = frozenset({"COMPLEX", "STRUCTURED", "PRIVATE_ASSET"})
_COMPLEX_PRODUCT_FLAGS = ("structured_product", "private_asset")


def proposed_shelf_rows(evidence_bundle: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    inputs = dict_at(evidence_bundle, "inputs")
    shelf_by_instrument = _shelf_rows_by_instrument(inputs)
    return {
        instrument_id: shelf_by_instrument.get(instrument_id)
        for instrument_id in _proposed_instrument_ids(inputs)
    }


def jurisdiction_allowed(shelf: dict[str, Any], jurisdiction: str) -> bool:
    eligibility = merged_product_policy(shelf, "eligibility")
    jurisdictions = {str(item) for item in list_at(eligibility, "jurisdictions")}
    return not jurisdictions or "GLOBAL" in jurisdictions or jurisdiction in jurisdictions


def client_segment_allowed(shelf: dict[str, Any], client_segment: str) -> bool:
    target_market = merged_product_policy(shelf, "target_market")
    segments = {str(item) for item in list_at(target_market, "client_segments")}
    return not segments or client_segment in segments or "PRIVATE_BANKING" in segments


def is_complex_or_private_product(shelf: dict[str, Any]) -> bool:
    attributes = dict_at(shelf, "attributes")
    return _complexity_classification(shelf, attributes) in _COMPLEX_PRODUCT_CLASSIFICATIONS or any(
        _truthy_product_flag(shelf, attributes, flag) for flag in _COMPLEX_PRODUCT_FLAGS
    )


def _shelf_rows_by_instrument(inputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("instrument_id")): row
        for row in list_at(inputs, "shelf_entries")
        if isinstance(row, dict) and row.get("instrument_id")
    }


def _proposed_instrument_ids(inputs: dict[str, Any]) -> list[str]:
    return [
        str(row.get("instrument_id"))
        for row in list_at(inputs, "proposed_trades")
        if isinstance(row, dict) and row.get("instrument_id")
    ]


def _complexity_classification(
    shelf: dict[str, Any],
    attributes: dict[str, Any],
) -> str:
    return str(
        shelf.get("complexity")
        or shelf.get("product_complexity")
        or attributes.get("complexity")
        or attributes.get("product_complexity")
        or ""
    ).upper()


def _truthy_product_flag(
    shelf: dict[str, Any],
    attributes: dict[str, Any],
    flag: str,
) -> bool:
    return bool(shelf.get(flag) or attributes.get(flag))


def merged_product_policy(shelf: dict[str, Any], key: str) -> dict[str, Any]:
    direct = dict_at(shelf, key)
    attributes = dict_at(shelf, "attributes")
    nested = dict_at(attributes, key)
    return cast(dict[str, Any], direct or nested)


__all__ = [
    "client_segment_allowed",
    "is_complex_or_private_product",
    "jurisdiction_allowed",
    "merged_product_policy",
    "proposed_shelf_rows",
]
