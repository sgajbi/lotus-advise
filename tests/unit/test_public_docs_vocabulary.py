from __future__ import annotations

from pathlib import Path

PUBLIC_DOCS = [
    Path("README.md"),
    Path("wiki/Advisory-Workspace.md"),
    Path("wiki/Proposal-Lifecycle.md"),
    Path("wiki/Integrations.md"),
    Path("wiki/Supported-Features.md"),
]


def test_public_docs_use_business_facing_integration_vocabulary() -> None:
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8").lower()
        assert " seam" not in text
        assert "seam " not in text
