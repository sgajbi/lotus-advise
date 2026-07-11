from pathlib import Path

SLICE14_PATH = Path(
    "docs/rfcs/RFC-0024-slice-14-data-product-promotion-and-supportability-hardening.md"
)
CAPABILITY_MODULE_PATHS = (
    Path("src/api/capabilities/service.py"),
    Path("src/api/capabilities/feature_catalog.py"),
    Path("src/api/capabilities/feature_catalog_foundation.py"),
    Path("src/api/capabilities/feature_catalog_evidence_products.py"),
    Path("src/api/capabilities/feature_catalog_operations.py"),
    Path("src/api/capabilities/workflow_catalog.py"),
    Path("src/api/capabilities/workflow_catalog_foundation.py"),
    Path("src/api/capabilities/workflow_catalog_evidence_products.py"),
    Path("src/api/capabilities/workflow_catalog_operations.py"),
)


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice14_data_product_promotion_is_indexed() -> None:
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = (
        "docs/rfcs/RFC-0024-slice-14-data-product-promotion-and-supportability-hardening.md"
    )

    assert SLICE14_PATH.exists()
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 14 is implemented" in wiki_index


def test_rfc0024_slice14_promotes_only_advisor_use_data_product() -> None:
    slice_text = _read(SLICE14_PATH)
    supported_features = _read("wiki/Supported-Features.md")
    commercial_text = _read("docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")

    assert "`AdvisoryProposalMemoEvidencePack:v1` as an active advisor-use evidence" in (slice_text)
    assert "advisory.proposals.memo_evidence_pack" in slice_text
    assert "advisory_proposal_memo_evidence_pack" in slice_text
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_features
    assert "Slice 14 is complete for active advisor-use memo data-product support" in (
        supported_features
    )
    assert "RFC-0028 now governs bank-demo/RFP proof through supported claims" in supported_features
    assert "without promoting client-ready memo publication" in supported_features
    assert "active governed advisor-use data product" in commercial_text
    assert "client-ready memo publication remains gated" in repo_context


def test_rfc0024_slice14_contracts_are_freshness_gated_without_client_ready_claims() -> None:
    telemetry_text = _read(
        "contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json"
    )
    declaration_text = _read("contracts/domain-data-products/lotus-advise-products.v1.json")
    capability_text = "\n".join(_read(path) for path in CAPABILITY_MODULE_PATHS)

    assert '"lifecycle_status": "active"' in declaration_text
    assert '"completeness_status": "complete"' in telemetry_text
    assert '"lineage_materialized": true' in telemetry_text
    assert '"freshness_state": "stale"' in telemetry_text
    assert '"blocked": true' in telemetry_text
    assert '"blocked_reason": "TRUST_TELEMETRY_STALE"' in telemetry_text
    assert "client-ready memo publication" in declaration_text
    assert "client-ready memo publication" in capability_text
    assert "client_ready_memo_publication" not in capability_text
