from __future__ import annotations

from pathlib import Path

PUBLIC_VOCABULARY_SURFACES = (
    Path(
        "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
    ),
    Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md"),
    Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md"),
    Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md"),
    Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md"),
    Path("docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md"),
    Path("wiki/RFC-Index.md"),
    Path("wiki/Supported-Features.md"),
    Path("wiki/API-Surface.md"),
    Path("src/api/main.py"),
    Path("src/api/proposals/routes_policy_packs.py"),
    Path("src/api/proposals/routes_policy_evaluations.py"),
    Path("src/core/advisor_cockpit/source_read_model.py"),
    Path("src/core/advisory_copilot/api_models.py"),
    Path("src/core/advisory_copilot/models.py"),
    Path("src/core/advisory_copilot/records.py"),
)

PUBLIC_WIKI_SURFACES = (
    Path("wiki/API-Surface.md"),
    Path("wiki/Operations-Runbook.md"),
    Path("wiki/RFC-Index.md"),
    Path("wiki/Security-and-Governance.md"),
    Path("wiki/Supported-Features.md"),
)


BANNED_CURRENT_STATE_PHRASES = (
    "first-wave",
    "planned later",
    "later slices",
    "later implementation slices",
    "second wave",
    "day-2",
    "wave-2",
    "placeholder task",
    "future scope for rfc-0024 through rfc-0028",
)

BANNED_PUBLIC_WIKI_TECHNICAL_PHRASES = (
    "raw prompt",
    "raw payload",
    "provider-response",
    "provider response",
)


def test_public_rfc0023_0028_surfaces_use_supported_scope_language() -> None:
    failures: list[str] = []

    for path in PUBLIC_VOCABULARY_SURFACES:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in BANNED_CURRENT_STATE_PHRASES:
            if phrase in text:
                failures.append(f"{path}: {phrase}")

    assert failures == []


def test_public_wiki_surfaces_use_business_safe_sensitive_data_language() -> None:
    failures: list[str] = []

    for path in PUBLIC_WIKI_SURFACES:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in BANNED_PUBLIC_WIKI_TECHNICAL_PHRASES:
            if phrase in text:
                failures.append(f"{path}: {phrase}")

    assert failures == []
