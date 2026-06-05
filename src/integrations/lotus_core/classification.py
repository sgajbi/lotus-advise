from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClassificationTaxonomy:
    labels_by_dimension: dict[str, dict[str, str]]
    taxonomy_version: str | None = None

    def has_dimension(self, dimension_name: str) -> bool:
        return bool(self.labels_by_dimension.get(classification_key(dimension_name)))


def normalized_optional_str(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def classification_key(value: Any) -> str:
    return "_".join(str(value or "").strip().upper().replace("-", " ").split())


def parse_classification_taxonomy(payload: dict[str, Any]) -> ClassificationTaxonomy:
    labels_by_dimension: dict[str, dict[str, str]] = {}
    records = payload.get("records")
    if not isinstance(records, list):
        records = []
    for record in records:
        if not isinstance(record, dict):
            continue
        dimension_name = classification_key(record.get("dimension_name"))
        dimension_value = classification_key(record.get("dimension_value"))
        if not dimension_name or not dimension_value:
            continue
        labels_by_dimension.setdefault(dimension_name, {})[dimension_value] = dimension_value
    return ClassificationTaxonomy(
        labels_by_dimension=labels_by_dimension,
        taxonomy_version=normalized_optional_str(payload.get("taxonomy_version")),
    )


def resolve_taxonomy_label(
    raw_value: Any,
    *,
    dimension_name: str,
    taxonomy: ClassificationTaxonomy | None,
    preserve_raw_when_ungoverned: bool = False,
) -> tuple[str, str | None]:
    raw_display_label = str(raw_value or "").strip()
    raw_label = classification_key(raw_value)
    if not raw_label:
        return "UNKNOWN", "missing_upstream_label"
    if taxonomy is None or not taxonomy.labels_by_dimension:
        return raw_display_label if preserve_raw_when_ungoverned else raw_label, None

    dimension_key = classification_key(dimension_name)
    governed_labels = taxonomy.labels_by_dimension.get(dimension_key)
    if not governed_labels:
        return (
            raw_display_label if preserve_raw_when_ungoverned else raw_label,
            "local_fallback_no_governed_taxonomy_dimension",
        )
    governed_label = governed_labels.get(raw_label)
    if governed_label:
        return governed_label, "lotus_core_classification_taxonomy"
    return "UNKNOWN", "missing_governed_taxonomy_label"


def classification_supportability_attributes(
    *,
    asset_class_source: str | None,
    product_type_source: str | None = None,
    taxonomy: ClassificationTaxonomy | None,
) -> dict[str, str]:
    attributes: dict[str, str] = {}
    if asset_class_source is not None:
        attributes["asset_class_source"] = asset_class_source
    if product_type_source is not None:
        attributes["product_type_source"] = product_type_source
    if taxonomy is not None and taxonomy.taxonomy_version:
        attributes["classification_taxonomy_version"] = taxonomy.taxonomy_version
    return attributes


def resolve_liquidity_tier(
    *,
    asset_class: Any,
    product_type: Any,
    sector: Any,
    rating: Any,
) -> str | None:
    asset_class_value = classification_key(asset_class)
    product_type_value = classification_key(product_type)
    sector_value = classification_key(sector)
    rating_value = classification_key(rating)

    for resolved_tier in (
        _cash_liquidity_tier(asset_class_value, product_type_value),
        _listed_product_liquidity_tier(asset_class_value, product_type_value),
        _bond_liquidity_tier(product_type_value, sector_value, rating_value),
        _fund_liquidity_tier(asset_class_value, product_type_value, sector_value),
        _fixed_income_liquidity_tier(asset_class_value, sector_value),
    ):
        if resolved_tier is not None:
            return resolved_tier
    return None


def _cash_liquidity_tier(asset_class_value: str, product_type_value: str) -> str | None:
    if asset_class_value == "CASH" or product_type_value == "CASH":
        return "L1"
    return None


def _listed_product_liquidity_tier(
    asset_class_value: str,
    product_type_value: str,
) -> str | None:
    if product_type_value == "ETF":
        return "L1"
    if product_type_value == "EQUITY" or asset_class_value == "EQUITY":
        return "L1"
    return None


def _bond_liquidity_tier(
    product_type_value: str,
    sector_value: str,
    rating_value: str,
) -> str | None:
    if product_type_value != "BOND":
        return None
    if sector_value == "GOVERNMENT":
        return "L1"
    if rating_value.startswith("A") or rating_value.startswith("BBB"):
        return "L2"
    return "L3"


def _fund_liquidity_tier(
    asset_class_value: str,
    product_type_value: str,
    sector_value: str,
) -> str | None:
    if product_type_value != "FUND" and asset_class_value != "FUND":
        return None
    if "PRIVATE" in sector_value:
        return "L5"
    if sector_value in {"FIXED_INCOME", "PRIVATE_CREDIT"}:
        return "L3"
    return "L2"


def _fixed_income_liquidity_tier(asset_class_value: str, sector_value: str) -> str | None:
    if asset_class_value != "FIXED_INCOME":
        return None
    if sector_value == "GOVERNMENT":
        return "L1"
    return "L2"


def prefer_upstream_liquidity_tier(
    *,
    raw_liquidity_tier: Any = None,
    enrichment_liquidity_tier: Any = None,
    asset_class: Any,
    product_type: Any,
    sector: Any,
    rating: Any,
) -> str | None:
    upstream_liquidity_tier = normalized_optional_str(
        raw_liquidity_tier
    ) or normalized_optional_str(enrichment_liquidity_tier)
    if upstream_liquidity_tier:
        return upstream_liquidity_tier
    return resolve_liquidity_tier(
        asset_class=asset_class,
        product_type=product_type,
        sector=sector,
        rating=rating,
    )
