from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE8_PATH = Path("docs/rfcs/RFC-0027-slice-8-copilot-run-review-audit-retention.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
MIGRATION_RUNBOOK_PATH = Path("docs/documentation/postgres-migration-rollout-runbook.md")
MIGRATION_STANDARD_PATH = Path("docs/standards/migration-contract.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice8_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-8-copilot-run-review-audit-retention.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice8 = _read(SLICE8_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - DOMAIN PERSISTENCE AND REVIEW AUDIT FOUNDATION ONLY" in slice8
    assert "does not expose public copilot APIs" in slice8
    assert "Advise API, Gateway, Workbench, data-product, canonical proof" in supported
    assert "supported product promotion remain unpromoted" in supported


def test_rfc0027_slice8_documents_audit_retention_and_raw_ai_storage_boundary() -> None:
    flat_slice8 = _flat(SLICE8_PATH)

    required = (
        "AdvisoryCopilotRunRecord",
        "AdvisoryCopilotReviewRecord",
        "persist_advisory_copilot_run",
        "record_advisory_copilot_review",
        "PostgresAdvisoryCopilotRepository",
        "advisory_copilot",
        "Raw prompt text, raw provider output, provider payloads",
        "ADVISORY_REVIEW_RECORD",
        "MODEL_RISK_AUDIT",
        "SUPPORTABILITY_DIAGNOSTIC",
        "seven years",
        "ninety days",
    )
    for item in required:
        assert item in flat_slice8


def test_rfc0027_slice8_migration_docs_include_copilot_namespace() -> None:
    runbook = _flat(MIGRATION_RUNBOOK_PATH)
    standard = _flat(MIGRATION_STANDARD_PATH)

    assert "advisory_copilot" in runbook
    assert "python scripts/postgres_migrate.py --target advisory_copilot" in runbook
    assert "Current namespaces: `proposals`, `advisory_copilot`" in standard
