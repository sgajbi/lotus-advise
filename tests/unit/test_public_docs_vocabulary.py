from __future__ import annotations

import re
from pathlib import Path

PUBLIC_DOCS = sorted(
    [
        *Path("wiki").glob("*.md"),
        *Path("docs/commercial").glob("*.md"),
        Path("docs/rfcs/README.md"),
        Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md"),
        Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md"),
        Path("docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md"),
    ],
    key=lambda path: path.as_posix(),
) + [
    Path("README.md"),
]
RFC_23_28_DOCS = sorted(
    Path("docs/rfcs").glob("RFC-002[3-8]*.md"),
    key=lambda path: path.as_posix(),
)


def test_public_docs_use_business_facing_integration_vocabulary() -> None:
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8").lower()
        assert " seam" not in text
        assert "seam " not in text
        assert re.search(r"\bdpm\b", text) is None
        assert "| todo |" not in text


def test_rfc23_28_docs_use_private_banking_portfolio_management_language() -> None:
    for path in RFC_23_28_DOCS:
        text = path.read_text(encoding="utf-8").lower()
        assert re.search(r"\bdpm\b", text) is None, path.as_posix()
