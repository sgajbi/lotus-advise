from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SECURITY_PATH = Path("wiki/Security-and-Governance.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_closure_preserves_slice_zero_decisions_and_no_open_questions() -> None:
    rfc = _read(RFC27_PATH)
    flat_rfc = _flat(RFC27_PATH)

    assert "IMPLEMENTED for governed internal advisor/reviewer copilot interactions" in rfc
    assert "Last Tightened** | 2026-05-31" in rfc
    assert "rfc0027-governed-advisory-ai-copilot" in rfc
    assert "Baseline gaps RFC-0027 closed or explicitly classified" in rfc
    assert "Current gaps that RFC-0027 must close" not in rfc
    assert "## 26. Slice 0 Pre-Implementation Decisions" in rfc
    assert "## 26. Open Questions" not in rfc
    assert "No open question may remain at final closure" in rfc

    required_decisions = (
        "An action family is not supported until its Advise API, Gateway route, Workbench surface",
        "RFC-0027 consumes implementation-backed RFC-0023 advisor-review narrative",
        "It does not implement or claim client-ready narrative",
        "Raw prompt text, unrestricted source payloads, raw provider responses, and unsafe output",
        "Gateway must expose `/api/v1/advisory-copilot/*` without calling `lotus-ai` directly",
        "There is no deferred follow-up bucket for data needed to prove the supported copilot",
        "Business-facing UI, report, wiki, and commercial material must use clean private-banking",
    )
    for decision in required_decisions:
        assert decision in flat_rfc


def test_rfc0027_commits_all_action_families_and_selected_api_surface() -> None:
    flat_rfc = _flat(RFC27_PATH)

    action_families = (
        "proposal explanation",
        "evidence Q&A",
        "advisor meeting preparation",
        "compliance review summary",
        "operations/report handoff summary",
        "client follow-up draft",
    )
    for family in action_families:
        assert family in flat_rfc

    selected_endpoints = (
        "POST /advisory/copilot/evidence-packets",
        "GET /advisory/copilot/evidence-packets/{evidence_packet_id}",
        "POST /advisory/copilot/actions",
        "GET /advisory/copilot/actions/{run_id}",
        "POST /advisory/copilot/actions/{run_id}/reviews",
        "GET /advisory/copilot/supportability",
        "GET /advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs",
        "/api/v1/advisory-copilot/*",
    )
    for endpoint in selected_endpoints:
        assert endpoint in flat_rfc

    assert "no free-form prompt endpoints exist" in flat_rfc
    assert "`lotus-advise` never calls model providers directly" in flat_rfc


def test_rfc0027_human_review_statuses_match_implemented_contract() -> None:
    flat_rfc = _flat(RFC27_PATH)

    implemented_statuses = (
        "REVIEW_REQUIRED",
        "APPROVED_FOR_INTERNAL_USE",
        "REJECTED",
        "SUPERSEDED",
        "EXPIRED",
        "UNSUPPORTED",
        "GUARDRAIL_REJECTED",
        "UNAVAILABLE",
    )
    for status in implemented_statuses:
        assert f"`{status}`" in flat_rfc

    unsupported_statuses = (
        "APPROVED_FOR_ADVISOR_USE",
        "APPROVED_FOR_CLIENT_DRAFT_USE",
        "REJECTED_UNSUPPORTED_EVIDENCE",
        "REJECTED_POLICY_OR_GUARDRAIL",
    )
    for status in unsupported_statuses:
        assert status not in flat_rfc


def test_rfc0027_requires_repeatable_seed_automation_and_lowest_layer_regression_tests() -> None:
    flat_rfc = _flat(RFC27_PATH)

    required_markers = (
        "RFC27_ADVISORY_COPILOT_CANONICAL",
        "PB_SG_GLOBAL_BAL_001",
        "seed and automation changes are RFC-0027 scope, not deferred work",
        "all six copilot action families return source-backed or explicitly unsupported posture",
        (
            "unsupported evidence, guardrail rejection, disabled or unavailable `lotus-ai`, "
            "review action"
        ),
        "no Workbench component reconstructs evidence, guardrails, review state, AI lineage",
        "every live defect found during validation is pinned by the lowest useful unit, contract",
        "every live validation issue discovered in this slice is fixed at the owning layer",
        "client-ready block posture",
    )
    for marker in required_markers:
        assert marker in flat_rfc


def test_rfc0027_pins_enterprise_backend_hardening_and_business_copy_rules() -> None:
    flat_rfc = _flat(RFC27_PATH)
    flat_wiki_security = _flat(WIKI_SECURITY_PATH)

    backend_quality_markers = (
        "remove dead code and unused paths",
        "break monolithic copilot code into clear domain modules",
        "reduce duplication across services, DTOs, mappers, validators, and tests",
        "keep business logic out of controllers and infrastructure layers",
        "improve batching, pagination, caching, and database access",
        "API design, versioning, idempotency, correlation IDs, auditability, lineage",
        "Swagger/OpenAPI examples, logging, metrics, tracing, operational diagnostics",
        "Evidence-section models and copilot structured-payload persistence reject raw prompt",
    )
    for marker in backend_quality_markers:
        assert marker in flat_rfc

    copy_markers = (
        "business-facing docs and UI/report copy explain advisor value",
        "without leaking raw prompts, provider details, internal run mechanics",
        "commercial material is truthful and implementation-backed",
        "clean private-banking language",
    )
    for marker in copy_markers:
        assert marker in flat_rfc

    assert "RFC-0027 Copilot Evidence Governance" in flat_wiki_security
    assert "UI, API, persistence, and replay paths aligned" in flat_wiki_security


def test_rfc0027_indexes_and_supported_features_promote_only_proven_internal_copilot() -> None:
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)
    rfc26 = _flat(RFC26_PATH)

    assert "IMPLEMENTED for source-owned advisor cockpit operating workflow" in rfc26
    assert (
        "RFC-0028 | Bank Demo Journey and Client-Ready Proof | "
        "IMPLEMENTED - bank-demo proof and claim-controlled commercial material complete"
        in rfc_index
    )
    expected_rfc27_row = (
        "RFC-0027 | Governed Advisory AI Copilot | IMPLEMENTED for governed internal "
        "advisor/reviewer copilot interactions; client-ready and execution authority remain gated"
    )
    assert expected_rfc27_row in rfc_index
    expected_rfc27_wiki_status = (
        "RFC-0027 is implemented for governed internal advisor/reviewer copilot interactions"
    )
    assert expected_rfc27_wiki_status in wiki_index
    assert "ADVISORY_COPILOT_CANONICAL_PROOF_CREATED" in wiki_index
    assert "Implemented for governed internal advisor/reviewer copilot interactions" in (
        supported_features
    )
    assert "AdvisoryCopilotInteractionRecord:v1" in supported_features
    assert "Client-ready publication, external client communication, policy approval/sign-off" in (
        supported_features
    )

    not_yet_implemented = rfc_index.split("## Not Yet Implemented", maxsplit=1)[1].split(
        "Recommended near-term implementation order", maxsplit=1
    )[0]
    assert "- `RFC-0026`" not in not_yet_implemented
    assert "- `RFC-0027`" not in not_yet_implemented
    assert "- `RFC-0028`" not in not_yet_implemented


def test_rfc0027_supported_features_ledger_reflects_implemented_closure_truth() -> None:
    rfc = _read(RFC27_PATH)
    ledger = rfc.split("## 20. Supported-Features Ledger", maxsplit=1)[1].split(
        "## 21. Implementation Closure", maxsplit=1
    )[0]
    flat_ledger = " ".join(ledger.split())

    assert "Current support posture" in ledger
    assert "Initial RFC state" not in ledger
    assert (
        "| Governed advisory copilot action catalog | Supported for supported internal "
        "advisor/reviewer actions |"
    ) in ledger
    assert "| Copilot evidence packet | Supported |" in ledger
    assert "| Gateway/Workbench copilot experience | Supported |" in ledger
    assert "No free-form prompt endpoint is supported" in flat_ledger
    assert "Raw prompts, unrestricted source payloads, and provider responses remain outside" in (
        flat_ledger
    )
    assert "| Proposed |" not in ledger
