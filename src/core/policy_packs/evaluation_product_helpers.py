from __future__ import annotations

from typing import Any, cast

from src.core.proposals.source_readiness_common import dict_at, list_at


def proposed_shelf_rows(evidence_bundle: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    inputs = dict_at(evidence_bundle, "inputs")
    shelf_by_instrument = {
        str(row.get("instrument_id")): row
        for row in list_at(inputs, "shelf_entries")
        if isinstance(row, dict) and row.get("instrument_id")
    }
    proposed = [
        str(row.get("instrument_id"))
        for row in list_at(inputs, "proposed_trades")
        if isinstance(row, dict) and row.get("instrument_id")
    ]
    return {instrument_id: shelf_by_instrument.get(instrument_id) for instrument_id in proposed}


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
    complexity = str(
        shelf.get("complexity")
        or shelf.get("product_complexity")
        or attributes.get("complexity")
        or attributes.get("product_complexity")
        or ""
    )
    return (
        complexity.upper() in {"COMPLEX", "STRUCTURED", "PRIVATE_ASSET"}
        or bool(shelf.get("structured_product") or attributes.get("structured_product"))
        or bool(shelf.get("private_asset") or attributes.get("private_asset"))
    )


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
