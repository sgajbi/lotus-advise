from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_rfc0025_slice3_documentation_records_non_promotional_data_product_posture() -> None:
    slice_doc = (
        REPO_ROOT / "docs" / "rfcs" / "RFC-0025-slice-3-data-product-and-platform-hardening.md"
    ).read_text(encoding="utf-8")
    rfc = (
        REPO_ROOT
        / "docs"
        / "rfcs"
        / "RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md"
    ).read_text(encoding="utf-8")
    supported = (REPO_ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")
    rfc_index = (REPO_ROOT / "wiki" / "RFC-Index.md").read_text(encoding="utf-8")

    assert "IMPLEMENTED - PROPOSED/BLOCKED DATA PRODUCT; NO POLICY SUPPORT PROMOTED" in slice_doc
    assert "`AdvisoryPolicyEvaluationRecord:v1`" in slice_doc
    assert "No policy row is added" in slice_doc
    assert "policy evaluation support is Planned" in supported
    assert "proposed, blocked data-product posture" in supported
    assert "RFC-0025 Slice 3 is implemented" in rfc_index
    assert "RFC-0025-slice-3-data-product-and-platform-hardening.md" in rfc


def test_rfc0025_policy_product_stays_proposed_blocked_without_capability_promotion() -> None:
    declaration = _load_json(
        REPO_ROOT / "contracts" / "domain-data-products" / "lotus-advise-products.v1.json"
    )
    telemetry = _load_json(
        REPO_ROOT
        / "contracts"
        / "trust-telemetry"
        / "advisory-policy-evaluation-record.telemetry.v1.json"
    )
    capability_text = (REPO_ROOT / "src" / "api" / "capabilities" / "service.py").read_text(
        encoding="utf-8"
    )

    product = next(
        item
        for item in declaration["products"]
        if item["product_name"] == "AdvisoryPolicyEvaluationRecord"
    )

    assert product["lifecycle_status"] == "proposed"
    assert product["current_routes"] == [
        "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations",
        "/advisory/policy-evaluations/review-queue",
        "/advisory/policy-evaluations/{evaluation_id}",
        "/advisory/policy-evaluations/{evaluation_id}/replay",
        "/advisory/policy-evaluations/{evaluation_id}/events",
        "/advisory/policy-evaluations/{evaluation_id}/lineage",
        "/advisory/policy-evaluations/{evaluation_id}/sign-off-package",
        "/advisory/policy-evaluations/{evaluation_id}/workflow",
        "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
        "/advisory/policy-evaluations/{evaluation_id}/report-packages",
        "/advisory/policy-evaluations/{evaluation_id}/ai-evidence",
    ]
    assert product["completeness_policy"]["default_status"] == "blocked"
    assert telemetry["blocking"]["blocked"] is True
    assert telemetry["completeness_status"] == "blocked"
    assert "advisory.proposals.policy_evaluation" not in capability_text
    assert "advisory_policy_evaluation" not in capability_text
