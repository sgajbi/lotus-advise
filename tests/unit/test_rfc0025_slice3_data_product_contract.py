from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flat(text: str) -> str:
    return " ".join(text.split())


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
    supported = _flat((REPO_ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8"))
    rfc_index = (REPO_ROOT / "wiki" / "RFC-Index.md").read_text(encoding="utf-8")

    assert "IMPLEMENTED - PROPOSED/BLOCKED DATA PRODUCT; NO POLICY SUPPORT PROMOTED" in slice_doc
    assert "`AdvisoryPolicyEvaluationRecord:v1`" in slice_doc
    assert "No policy row is added" in slice_doc
    assert "policy evaluation support is Planned" in supported
    assert "proposed, blocked data-product posture" in supported
    assert "RFC-0025 Slice 3 is implemented" in rfc_index
    assert "RFC-0025-slice-3-data-product-and-platform-hardening.md" in rfc


def test_rfc0025_slice3_records_historical_proposed_blocked_posture() -> None:
    declaration = _load_json(
        REPO_ROOT / "contracts" / "domain-data-products" / "lotus-advise-products.v1.json"
    )
    telemetry = _load_json(
        REPO_ROOT
        / "contracts"
        / "trust-telemetry"
        / "advisory-policy-evaluation-record.telemetry.v1.json"
    )
    slice_doc = (
        REPO_ROOT / "docs" / "rfcs" / "RFC-0025-slice-3-data-product-and-platform-hardening.md"
    ).read_text(encoding="utf-8")

    product = next(
        item
        for item in declaration["products"]
        if item["product_name"] == "AdvisoryPolicyEvaluationRecord"
    )

    assert "Lifecycle status | `proposed`" in slice_doc
    assert "Completeness default | `blocked`" in slice_doc
    assert "`freshness_state` is `unknown`" in slice_doc
    assert "`completeness_status` is `blocked`" in slice_doc
    assert "`blocking.blocked` is `true`" in slice_doc
    assert "No policy row is added" in slice_doc
    assert product["lifecycle_status"] == "active"
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
    assert product["completeness_policy"]["default_status"] == "complete"
    assert telemetry["blocking"]["blocked"] is True
    assert telemetry["blocking"]["blocked_reason"] == "TRUST_TELEMETRY_STALE"
    assert telemetry["completeness_status"] == "complete"
