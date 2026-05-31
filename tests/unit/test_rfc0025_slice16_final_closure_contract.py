from __future__ import annotations

import json
from pathlib import Path

SLICE16_PATH = Path("docs/rfcs/RFC-0025-slice-16-final-closure.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_rfc0025_slice16_closure_is_indexed() -> None:
    rfc_text = _read("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0025-slice-16-final-closure.md"

    assert SLICE16_PATH.exists()
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0025 Slice 16 is implemented as final closure" in wiki_index


def test_rfc0025_slice16_closes_policy_evidence_without_client_ready_claims() -> None:
    slice_text = _read(SLICE16_PATH)
    supported_features = _read("wiki/Supported-Features.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")
    readme = _read("README.md")

    required_terms = [
        "RFC-0025 is implemented for advisor/compliance policy evaluation evidence",
        "client-ready policy document publication is not supported",
        "external client communication is not supported",
        "full RFC-0028 bank-demo/RFP package claims remain gated",
        "No Lotus agent context, skill, or procedural guidance change is required",
    ]
    for term in required_terms:
        assert term in slice_text

    assert "RFC-0025 is implemented for advisor/compliance policy evidence through Slice 17" in (
        supported_features
    )
    assert "client-ready policy publication, and external client communication" in (
        supported_features
    )
    assert "RFC-0028 governs bank-demo/RFP proof through supported claims" in supported_features
    assert "RFC-0025 enterprise policy-pack implementation is closed" in repo_context
    assert "AdvisoryPolicyEvaluationRecord:v1` is an active advisor/compliance policy evidence" in (
        readme
    )


def test_rfc0025_slice16_promotes_active_policy_data_product_truth() -> None:
    telemetry = _load_json(
        "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
    )
    declaration = _load_json("contracts/domain-data-products/lotus-advise-products.v1.json")
    capabilities = _read("src/api/capabilities/service.py")
    supportability = _read("src/core/policy_packs/supportability.py")

    product = next(
        item
        for item in declaration["products"]
        if item["product_name"] == "AdvisoryPolicyEvaluationRecord"
    )

    assert product["lifecycle_status"] == "active"
    assert product["completeness_policy"] == {
        "default_status": "complete",
        "partial_allowed": False,
    }
    assert (
        "client-ready publication, and external client communication remain blocked"
        in (product["freshness_policy"]["max_allowed_age_description"])
    )

    assert telemetry["freshness"]["freshness_state"] == "current"
    assert telemetry["completeness_status"] == "complete"
    assert telemetry["data_quality_status"] == "quality_passed"
    assert telemetry["blocking"] == {"blocked": False}
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-16-final-closure.md"
        in telemetry["lineage"]["evidence_uris"]
    )
    assert "completed policy sign-off authority" in telemetry["evidence"]["claim_boundary"]
    assert "client-ready publication" in telemetry["evidence"]["claim_boundary"]

    assert "advisory.proposals.policy_evaluation" in capabilities
    assert "advisory_policy_evaluation" in capabilities
    assert "SUPPORTED_BY_RFC0025_SLICE16_FINAL_CLOSURE" in supportability
    assert "CLIENT_READY_PUBLICATION_POSTURE" in supportability
