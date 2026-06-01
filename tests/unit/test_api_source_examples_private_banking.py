from __future__ import annotations

from pathlib import Path

ACTIVE_API_SOURCE_ROOTS = (
    Path("src/api"),
    Path("src/core"),
)

LEGACY_PORTFOLIO_EXAMPLE_FRAGMENTS = (
    "pf_advisory_01",
    "pf_advisory_demo",
    "DEMO_DPM",
)


def test_active_api_source_examples_use_canonical_private_banking_portfolio() -> None:
    failures: list[str] = []

    for root in ACTIVE_API_SOURCE_ROOTS:
        for path in sorted(root.rglob("*.py"), key=lambda candidate: candidate.as_posix()):
            text = path.read_text(encoding="utf-8")
            for fragment in LEGACY_PORTFOLIO_EXAMPLE_FRAGMENTS:
                if fragment in text:
                    failures.append(f"{path.as_posix()}: {fragment}")

    assert failures == []
