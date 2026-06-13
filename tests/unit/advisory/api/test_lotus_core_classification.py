from __future__ import annotations

from src.integrations.lotus_core.classification import (
    ClassificationTaxonomy,
    parse_classification_taxonomy,
    resolve_taxonomy_label,
)


def test_parse_classification_taxonomy_normalizes_valid_records_only() -> None:
    taxonomy = parse_classification_taxonomy(
        {
            "taxonomy_version": " rfc_062_v1 ",
            "records": [
                {"dimension_name": "Asset Class", "dimension_value": "Fixed-Income"},
                {"dimension_name": "Asset Class", "dimension_value": ""},
                {"dimension_name": "", "dimension_value": "Equity"},
                "not-a-record",
            ],
        }
    )

    assert taxonomy.taxonomy_version == "rfc_062_v1"
    assert taxonomy.labels_by_dimension == {"ASSET_CLASS": {"FIXED_INCOME": "FIXED_INCOME"}}


def test_resolve_taxonomy_label_marks_missing_upstream_value_unknown() -> None:
    label, source = resolve_taxonomy_label(
        "",
        dimension_name="Asset Class",
        taxonomy=None,
    )

    assert label == "UNKNOWN"
    assert source == "missing_upstream_label"


def test_resolve_taxonomy_label_uses_normalized_label_without_taxonomy() -> None:
    label, source = resolve_taxonomy_label(
        "Fixed-Income",
        dimension_name="Asset Class",
        taxonomy=None,
    )

    assert label == "FIXED_INCOME"
    assert source is None


def test_resolve_taxonomy_label_can_preserve_raw_label_without_taxonomy() -> None:
    label, source = resolve_taxonomy_label(
        "Fixed-Income",
        dimension_name="Asset Class",
        taxonomy=None,
        preserve_raw_when_ungoverned=True,
    )

    assert label == "Fixed-Income"
    assert source is None


def test_resolve_taxonomy_label_falls_back_when_dimension_is_not_governed() -> None:
    taxonomy = ClassificationTaxonomy(labels_by_dimension={"PRODUCT_TYPE": {"BOND": "BOND"}})

    label, source = resolve_taxonomy_label(
        "Fixed-Income",
        dimension_name="Asset Class",
        taxonomy=taxonomy,
    )

    assert label == "FIXED_INCOME"
    assert source == "local_fallback_no_governed_taxonomy_dimension"


def test_resolve_taxonomy_label_uses_governed_taxonomy_match() -> None:
    taxonomy = ClassificationTaxonomy(
        labels_by_dimension={"ASSET_CLASS": {"FIXED_INCOME": "FIXED_INCOME"}}
    )

    label, source = resolve_taxonomy_label(
        "Fixed-Income",
        dimension_name="Asset Class",
        taxonomy=taxonomy,
    )

    assert label == "FIXED_INCOME"
    assert source == "lotus_core_classification_taxonomy"


def test_resolve_taxonomy_label_rejects_missing_governed_value() -> None:
    taxonomy = ClassificationTaxonomy(labels_by_dimension={"ASSET_CLASS": {"EQUITY": "EQUITY"}})

    label, source = resolve_taxonomy_label(
        "Fixed-Income",
        dimension_name="Asset Class",
        taxonomy=taxonomy,
    )

    assert label == "UNKNOWN"
    assert source == "missing_governed_taxonomy_label"
