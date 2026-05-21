from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WTBD_PATH = REPO_ROOT / "docs" / "rfcs" / "WTBD.md"


def _wtbd_sections(text: str) -> dict[str, str]:
    headings = list(re.finditer(r"^## (WTBD-\d{3}): .+$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[heading.group(1)] = text[heading.start() : end]
    return sections


def test_wtbd_ledger_has_explicit_closed_status_for_each_recorded_item():
    text = WTBD_PATH.read_text(encoding="utf-8")
    sections = _wtbd_sections(text)

    assert sections, "WTBD ledger must contain at least one recorded WTBD section."
    assert set(sections) == {"WTBD-001", "WTBD-002", "WTBD-003", "WTBD-004"}

    for wtbd_id, section in sections.items():
        assert "- Status: Closed" in section, f"{wtbd_id} must carry an explicit closure status."
        assert re.search(
            rf"\| {wtbd_id} \| [^|]+ \| Closed \| [^|]+ \|",
            text,
        ), f"{wtbd_id} must be represented as closed in the closure register."


def test_wtbd_ledger_does_not_leave_observation_only_or_unconfirmed_defect_language_open():
    text = WTBD_PATH.read_text(encoding="utf-8")

    stale_open_phrases = (
        "read-only observation only",
        "not a confirmed defect today",
        "remains the only explicit downstream-owner item",
    )
    for phrase in stale_open_phrases:
        assert phrase not in text
