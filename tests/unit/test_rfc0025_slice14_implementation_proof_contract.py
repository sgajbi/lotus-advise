from pathlib import Path

SLICE14_PATH = Path("docs/rfcs/RFC-0025-slice-14-implementation-proof.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0025_slice14_implementation_proof_is_indexed() -> None:
    slice14_text = _read(SLICE14_PATH)
    rfc_text = _read("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")
    supported_features = _read("wiki/Supported-Features.md")

    source_ref = "docs/rfcs/RFC-0025-slice-14-implementation-proof.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index

    assert "proposal_policy" in slice14_text
    assert "policy evaluation create/read/review-queue/workflow/sign-off-package" in slice14_text
    assert "sign-off-decision/report-package/AI-evidence/lineage/replay" in slice14_text
    assert "SG_PRIVATE_BANKING_REFERENCE" in slice14_text
    assert "client-ready policy document request rejection" in slice14_text
    assert "POLICY_AI_EVIDENCE_FORBIDDEN_ACTION" in slice14_text
    assert "raw_source_evidence_included=false" in slice14_text
    assert "replay evidence with exact evaluation hash" in slice14_text
    assert "live-suite `proposal_policy` proof" in supported_features
    assert "RFC-0025 is implemented for advisor/compliance policy evidence through Slice 16" in (
        supported_features
    )


def test_rfc0025_slice14_records_proof_before_slice16_product_promotion() -> None:
    telemetry_text = _read(
        "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
    )
    declaration_text = _read("contracts/domain-data-products/lotus-advise-products.v1.json")
    context_text = _read("REPOSITORY-ENGINEERING-CONTEXT.md")
    capability_text = _read("src/api/capabilities/service.py")

    assert "RFC-0025-slice-14-implementation-proof.md" in telemetry_text
    assert "live-suite proof" in telemetry_text
    assert "final closure evidence" in declaration_text
    assert "canonical live proof" not in declaration_text
    assert "live-suite policy implementation proof" in context_text
    assert '"completeness_status": "complete"' in telemetry_text
    assert "active advisor/compliance policy evidence data product" in telemetry_text
    assert "approval/waiver authority" in telemetry_text
    assert "completed policy sign-off authority" in telemetry_text
    assert "client-ready publication" in telemetry_text
    assert "advisory.proposals.policy_evaluation" in capability_text
    assert "advisory_policy_evaluation" in capability_text
