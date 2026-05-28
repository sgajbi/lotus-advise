from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE3_PATH = Path("docs/rfcs/RFC-0027-slice-3-data-product-and-platform-hardening.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
TRUST_TELEMETRY_README_PATH = Path("contracts/trust-telemetry/README.md")
FINAL_CLOSURE_PATH = Path(
    "docs/rfcs/RFC-0027-slice-10-14-product-realization-proof-closure.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice3_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-3-data-product-and-platform-hardening.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice3 = _read(SLICE3_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - NON-PROMOTING DATA-PRODUCT POSTURE" in slice3
    assert "does not declare `AdvisoryCopilotInteractionRecord:v1`" in slice3
    assert "does not add copilot trust telemetry" in slice3
    assert "does not promote `/platform/capabilities` copilot support" in slice3
    assert "Slices 10-14 close Gateway publication" in flat_supported
    assert "active `AdvisoryCopilotInteractionRecord:v1` data-product posture" in flat_supported


def test_rfc0027_slice3_records_promotion_requirements() -> None:
    flat_slice3 = _flat(SLICE3_PATH)

    requirements = (
        "runtime action APIs",
        "durable evidence-packet and run persistence",
        "review-state persistence",
        "guardrail and unsupported-evidence outcomes",
        "`lotus-ai` workflow-pack lineage",
        "Gateway routing",
        "Workbench Gateway-first product surface",
        "`RFC27_ADVISORY_COPILOT_CANONICAL` live proof",
        "SLO, access, retention, and evidence-policy posture",
        "trust telemetry",
        "`/platform/capabilities` promotion",
        "platform mesh certification",
    )
    for requirement in requirements:
        assert requirement in flat_slice3


def test_rfc0027_slice3_records_negative_governance_tests() -> None:
    flat_slice3 = _flat(SLICE3_PATH)

    assert "tests/unit/scripts/test_validate_domain_data_product_declarations.py" in flat_slice3
    assert "test_rfc0027_copilot_products_are_not_promoted_before_runtime_proof" in flat_slice3
    assert "tests/unit/advisory/api/test_api_integration_capabilities.py" in flat_slice3
    assert "test_rfc0027_capabilities_do_not_promote_copilot_before_runtime_proof" in flat_slice3
    assert "no copilot trust telemetry snapshot exists yet" in flat_slice3


def test_rfc0027_final_closure_promotes_only_interaction_record() -> None:
    final_closure = _flat(FINAL_CLOSURE_PATH)
    trust_readme = _flat(TRUST_TELEMETRY_README_PATH)

    assert "AdvisoryCopilotInteractionRecord:v1" in final_closure
    assert "Evidence packets and review events remain audit records" in final_closure
    assert "client-ready publication" in final_closure
    assert "AdvisoryCopilotInteractionRecord:v1" in trust_readme
    assert "client-ready publication" in trust_readme
