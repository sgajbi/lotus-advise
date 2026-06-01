from pathlib import Path

from tests.unit.capability_source_helpers import read_capability_source

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE10_PATH = Path("docs/rfcs/RFC-0025-slice-10-report-render-archive-realization.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
ROUTE_SOURCE_PATH = Path("src/api/proposals/routes_policy_evaluations.py")
REPORTING_SOURCE_PATH = Path("src/core/policy_packs/reporting.py")
REPORTING_MODELS_SOURCE_PATH = Path("src/core/policy_packs/reporting_models.py")
REPORT_ADAPTER_SOURCE_PATH = Path("src/integrations/lotus_report/adapter.py")
REPORT_MAPPING_SOURCE_PATH = Path("src/integrations/lotus_report/request_mapping.py")
MODELS_SOURCE_PATH = Path("src/core/policy_packs/models.py")
DECLARATION_PATH = Path("contracts/domain-data-products/lotus-advise-products.v1.json")
TELEMETRY_PATH = Path(
    "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice10_policy_report_package_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice10_text = SLICE10_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-10-report-render-archive-realization.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Scope Boundary",
        "## Implementation",
        "## Lineage Event",
        "## Data Product Posture",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    ):
        assert section in slice10_text

    assert "IMPLEMENTED - ADVISE REPORT-PACKAGE REALIZATION ONLY" in slice10_text
    assert "client-ready document requests fail closed" in slice10_text
    assert "Gateway/Workbench policy consumption" in slice10_text


def test_rfc0025_slice10_records_report_refs_without_product_surface_promotion() -> None:
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8"))
    routes_source = ROUTE_SOURCE_PATH.read_text(encoding="utf-8")
    reporting_source = REPORTING_SOURCE_PATH.read_text(encoding="utf-8")
    reporting_models_source = REPORTING_MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    adapter_source = REPORT_ADAPTER_SOURCE_PATH.read_text(encoding="utf-8")
    mapping_source = REPORT_MAPPING_SOURCE_PATH.read_text(encoding="utf-8")
    compatibility_models_source = MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    declaration_source = DECLARATION_PATH.read_text(encoding="utf-8")
    telemetry_source = TELEMETRY_PATH.read_text(encoding="utf-8")
    capabilities_source = read_capability_source()

    assert "/advisory/policy-evaluations/{evaluation_id}/report-packages" in routes_source
    assert "PolicyEvaluationReportPackageRequest" in reporting_models_source
    assert "PolicyEvaluationReportPackageResponse" in reporting_models_source
    assert "PolicyEvaluationReportPackageRequest" in compatibility_models_source
    assert "PolicyEvaluationReportPackageResponse" in compatibility_models_source
    assert "rfc0025.policy-report-package-realization.v1" in reporting_source
    assert "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED" in reporting_source
    assert "POLICY_CLIENT_READY_DOCUMENT_NOT_SUPPORTED" in reporting_source
    assert "ADVISORY_POLICY_SIGN_OFF_PACKAGE" in mapping_source
    assert "request_policy_sign_off_report_package_with_lotus_report" in adapter_source
    assert "/advisory/policy-evaluations/{evaluation_id}/report-packages" in declaration_source
    assert "RFC-0025-slice-10-report-render-archive-realization.md" in telemetry_source
    assert "src/core/policy_packs/reporting.py" in telemetry_source
    assert "policy report-package realization" in supported_features
    assert "report/render/archive refs are recorded in policy lineage" in supported_features
    assert "client-ready document requests fail closed" in supported_features
    assert (
        "Slice 12 is complete for Gateway and Workbench product realization" in supported_features
    )
    assert "active data-product promotion" in supported_features
    assert "client-ready publication" in supported_features
    assert "advisory.proposals.policy_evaluation" in capabilities_source
    assert "advisory_policy_evaluation" in capabilities_source
