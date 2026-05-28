from __future__ import annotations

from pathlib import Path

RFC28_PATH = Path("docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0028_locks_slice_zero_decisions_before_implementation() -> None:
    rfc = _read(RFC28_PATH)
    flat = _flat(RFC28_PATH)

    assert "Last Tightened** | 2026-05-28" in rfc
    assert "rfc0028-gold-standard-implementation" in rfc
    assert "## 22. Slice 0 Pre-Implementation Decisions" in rfc
    assert "## 22. Open Questions" not in rfc
    assert "No open implementation question remains for RFC-0028 Slice 1" in rfc

    required_decisions = (
        "Hybrid. `lotus-advise` must implement an Advise-owned proof-pack and supported-claim API",
        "Script-only proof is insufficient for RFC-0028",
        "Primary dataset is `PB_SG_GLOBAL_BAL_001`",
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "First supported journey is the combined private-banking advisory scenario",
        "No Workbench component may reconstruct advisory suitability, memo, narrative, policy",
        "CLIENT_READY_REVIEW_REQUIRED",
        "CLIENT_READY_PUBLICATION_BLOCKED",
        "External certifications, bank-specific control attestations, SOC/ISO status",
        "Load, latency, SLO, DR/RTO/RPO, tenant, and legal-entity claims block closure only",
        (
            "Produce markdown source now for demo script, proof interpretation guide, "
            "RFP/security pack"
        ),
    )
    for decision in required_decisions:
        assert decision in flat


def test_rfc0028_requires_canonical_front_office_automation_and_lowest_layer_tests() -> None:
    flat = _flat(RFC28_PATH)

    automation_markers = (
        "RFC-0028 must expand canonical front-office automation",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "PB_SG_GLOBAL_BAL_001",
        "WorkBench evidence is not demo-ready",
    )
    for marker in automation_markers:
        assert marker.lower() in flat.lower()

    test_markers = (
        "Any live validation defect discovered during RFC-0028 must be covered",
        "unit for pure domain rules",
        "contract/API test for schema and route behavior",
        "integration test for cross-service contracts",
        "front-office/live validation for product-surface regressions",
    )
    for marker in test_markers:
        assert marker in flat


def test_rfc0028_records_platform_slice_one_supported_claim_scaffolding() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "A reusable platform gap exists",
        "1f46cd764b1e8437091c6d5e567403053b899313",
        "ea6e8151d253f5d738dfb5902d8193238b946bba",
        "PR #366",
        "26554797152",
        "supported-claim-register.schema.json",
        "validate_supported_claim_register.py",
        "test_supported_claim_register_contract.py",
        "No Advise-local claim taxonomy may diverge from the platform validator",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_indexes_record_platform_slice_one_without_promotion() -> None:
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    index_markers = (
        "DRAFT - SLICES 0-6 COMPLETE",
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "PB_SG_GLOBAL_BAL_001",
        "PR #366",
        "26554797152",
    )
    for marker in index_markers:
        assert marker in rfc_index
        assert marker in wiki_index or marker in supported_features

    assert "No Gateway, Workbench, screenshot, RFP/security" in supported_features
    assert "bank-demo/RFP, screenshot, product one-pager" in wiki_index
    assert "DRAFT - SLICE 0 DECISIONS LOCKED" not in rfc_index
    assert "DRAFT - SLICE 0 DECISIONS LOCKED" not in wiki_index
    assert "Draft with Slice 0 decisions locked" not in supported_features


def test_rfc0028_records_slice_two_cleanup_scope_and_wiki_gate() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "The first cleanup gap was durable documentation drift after Slice 1",
        "docs/rfcs/README.md",
        "wiki/RFC-Index.md",
        "wiki/Supported-Features.md",
        (
            "No Advise runtime code, controller, infrastructure module, "
            "or commercial asset was created"
        ),
        "Wiki source changed because supported-feature and RFC-index truth changed",
        "publication must happen after merge to `main`",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_records_slice_four_proof_model_implementation() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "src/core/bank_demo_proof/",
        "AdvisoryDemoScenarioContract:v1",
        "AdvisorySupportedClaimRegister:v1",
        "AdvisoryBankDemoProofPack:v1",
        "No controller, API route, persistence table, data-product declaration",
        "IMPLEMENTATION_BACKED` claims require evidence refs and proof requirements",
        "local-only or secret runtime assets cannot be commit-allowed",
        "CLIENT_READY_APPROVED` remains blocked",
        "tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_records_slice_five_backend_proof_capture() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "src/core/bank_demo_proof/capture.py",
        "scripts/capture_rfc0028_backend_proof.py",
        "output/rfc0028/backend-proof",
        "metadata.json",
        "scenario-contract.json",
        "supported-claim-register.json",
        "proof-pack.json",
        "runtime-posture.json",
        "sanitized-runtime-summary.json",
        "material-field-review.json",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "RFC0028_BACKEND_MATERIAL_FIELD_REVIEW_PASSED",
        "RFC0028_RUNTIME_POSTURE_CAPTURED",
        "CLIENT_READY_PUBLICATION_BLOCKED",
        "BACKEND_BACKED_UI_PENDING",
        "tests/unit/advisory/engine/test_engine_bank_demo_proof_capture.py",
        "tests/unit/scripts/test_capture_rfc0028_backend_proof.py",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_records_slice_six_document_proof_capture() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    markers = (
        "AdvisoryDocumentProofSummary:v1",
        "src/core/bank_demo_proof/document_proof.py",
        "document-proof-summary.json",
        "RFC0028_DOCUMENT_PROOF_SUMMARY_CREATED",
        "advisor_use_document_proof_available",
        "BACKEND_BACKED_UI_PENDING",
        "OWNED_BY_LOTUS_ARCHIVE",
        "MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
        "POLICY_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
        "tests/unit/advisory/engine/test_engine_bank_demo_document_proof.py",
    )
    for marker in markers:
        assert marker in flat

    for source in (rfc_index, wiki_index, supported_features):
        assert "DRAFT - SLICES 0-6 COMPLETE" in source or "Slices 0-6 complete" in source
        assert "document-proof-summary.json" in source
        assert "client-ready document publication remains blocked" in source


def test_rfc0028_records_slice_seven_a_advise_proof_api_without_gateway_overclaim() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    markers = (
        "Slice 7A Advise source API implementation decision and evidence",
        "GET /advisory/bank-demo-proof/scenario-contract",
        "GET /advisory/bank-demo-proof/supported-claim-register",
        "POST /advisory/bank-demo-proof/proof-packs",
        "src/api/routers/bank_demo_proof.py",
        "BackendProofCaptureBundle",
        "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED",
        "HTTP 409",
        "tests/unit/advisory/api/test_api_bank_demo_proof.py",
    )
    for marker in markers:
        assert marker in flat

    for source in (rfc_index, wiki_index, supported_features):
        assert "SLICE 7A ADVISE API COMPLETE" in source or "Slice 7A Advise API complete" in source
        assert "Gateway consumption remains the next Slice 7 owner-repository step" in source
        assert "screenshot" in source
        assert "RFP" in source
        assert "client-ready publication claims unpromoted" in source or (
            "client-ready publication claim is promoted" in source
        )
