from __future__ import annotations

from typing import Any

from src.core.portfolio_models import ShelfEntry
from src.integrations.lotus_core.classification import (
    ClassificationTaxonomy,
    classification_supportability_attributes,
    normalized_optional_str,
    prefer_upstream_liquidity_tier,
    resolve_taxonomy_label,
)
from src.integrations.lotus_core.stateful_context_payload_values import (
    mapping_rows,
    normalized_text,
)


def shelf_attributes_from_payload(
    *,
    sector: Any = None,
    country: Any = None,
    product_type: Any = None,
    rating: Any = None,
    ultimate_parent_issuer_id: Any = None,
    ultimate_parent_issuer_name: Any = None,
) -> dict[str, str]:
    attributes = {"source": "LOTUS_CORE_STATEFUL_CONTEXT"}
    optional_values = {
        "sector": sector,
        "country": country,
        "product_type": product_type,
        "rating": rating,
        "ultimate_parent_issuer_id": ultimate_parent_issuer_id,
        "ultimate_parent_issuer_name": ultimate_parent_issuer_name,
    }
    for key, raw_value in optional_values.items():
        value = normalized_text(raw_value)
        if value:
            attributes[key] = value
    return attributes


def build_shelf_entries(
    *,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
    enrichment_by_instrument_id: dict[str, dict[str, Any]] | None = None,
    classification_taxonomy: ClassificationTaxonomy | None = None,
) -> list[ShelfEntry]:
    shelf_by_instrument: dict[str, ShelfEntry] = {}
    enrichment_rows = enrichment_by_instrument_id or {}
    for raw_position in mapping_rows(positions_payload, "positions"):
        shelf_entry = _position_shelf_entry(
            raw_position,
            enrichment_by_instrument_id=enrichment_rows,
            classification_taxonomy=classification_taxonomy,
        )
        if shelf_entry is not None:
            shelf_by_instrument[shelf_entry.instrument_id] = shelf_entry
    for account in mapping_rows(cash_payload, "cash_accounts"):
        shelf_entry = _cash_shelf_entry(account)
        if shelf_entry is not None:
            shelf_by_instrument[shelf_entry.instrument_id] = shelf_entry
    return list(shelf_by_instrument.values())


def _position_shelf_entry(
    raw_position: dict[str, Any],
    *,
    enrichment_by_instrument_id: dict[str, dict[str, Any]],
    classification_taxonomy: ClassificationTaxonomy | None,
) -> ShelfEntry | None:
    instrument_id = normalized_text(raw_position.get("security_id"))
    if not instrument_id:
        return None
    asset_class, asset_class_source = resolve_taxonomy_label(
        raw_position.get("asset_class"),
        dimension_name="asset_class",
        taxonomy=classification_taxonomy,
    )
    product_type, product_type_source = resolve_taxonomy_label(
        raw_position.get("product_type"),
        dimension_name="product_type",
        taxonomy=classification_taxonomy,
        preserve_raw_when_ungoverned=True,
    )
    enrichment_row = enrichment_by_instrument_id.get(instrument_id, {})
    return ShelfEntry(
        instrument_id=instrument_id,
        status="APPROVED",
        asset_class=asset_class,
        issuer_id=normalized_optional_str(
            _prefer_position_value(raw_position, enrichment_row, "issuer_id")
        ),
        liquidity_tier=prefer_upstream_liquidity_tier(
            raw_liquidity_tier=raw_position.get("liquidity_tier"),
            enrichment_liquidity_tier=enrichment_row.get("liquidity_tier"),
            asset_class=asset_class,
            product_type=product_type,
            sector=raw_position.get("sector"),
            rating=raw_position.get("rating"),
        ),
        attributes=(
            _position_shelf_attributes(raw_position, enrichment_row, product_type=product_type)
            | classification_supportability_attributes(
                asset_class_source=asset_class_source,
                product_type_source=product_type_source,
                taxonomy=classification_taxonomy,
            )
        ),
    )


def _position_shelf_attributes(
    raw_position: dict[str, Any],
    enrichment_row: dict[str, Any],
    *,
    product_type: str,
) -> dict[str, str]:
    return shelf_attributes_from_payload(
        sector=raw_position.get("sector"),
        country=raw_position.get("country_of_risk"),
        product_type=product_type,
        rating=raw_position.get("rating"),
        ultimate_parent_issuer_id=_prefer_position_value(
            raw_position,
            enrichment_row,
            "ultimate_parent_issuer_id",
        ),
        ultimate_parent_issuer_name=_prefer_position_value(
            raw_position,
            enrichment_row,
            "ultimate_parent_issuer_name",
        ),
    )


def _prefer_position_value(
    raw_position: dict[str, Any],
    enrichment_row: dict[str, Any],
    key: str,
) -> Any:
    if raw_position.get(key) is not None:
        return raw_position.get(key)
    return enrichment_row.get(key)


def _cash_shelf_entry(account: dict[str, Any]) -> ShelfEntry | None:
    instrument_id = normalized_text(account.get("instrument_id") or account.get("security_id"))
    if not instrument_id:
        return None
    return ShelfEntry(
        instrument_id=instrument_id,
        status="APPROVED",
        asset_class="CASH",
        issuer_id=normalized_optional_str(account.get("issuer_id")),
        liquidity_tier=prefer_upstream_liquidity_tier(
            raw_liquidity_tier=account.get("liquidity_tier"),
            asset_class="CASH",
            product_type="Cash",
            sector=None,
            rating=None,
        ),
        attributes=shelf_attributes_from_payload(product_type="Cash"),
    )
