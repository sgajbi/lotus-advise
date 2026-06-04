from __future__ import annotations

from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[4] / "src" / "core" / "advisory"


def _read(module_name: str) -> str:
    return (SOURCE_ROOT / module_name).read_text(encoding="utf-8")


def test_proposal_narrative_public_module_stays_orchestration_only() -> None:
    narrative = _read("narrative.py")
    grounding = _read("narrative_grounding.py")
    sections = _read("narrative_sections.py")
    ai = _read("narrative_ai.py")

    assert "build_proposal_narrative_grounding_packet" in narrative
    assert "render_sections" in narrative
    assert "apply_ai_draft_sections" in narrative

    for helper_name in (
        "def _facts_from_artifact",
        "def _source_refs",
        "def _missing_evidence",
        "def _executive_summary_text",
        "def _alternatives_text",
        "def apply_ai_draft_sections",
    ):
        assert helper_name not in narrative

    assert "def _facts_from_artifact" in grounding
    assert "def _missing_evidence" in grounding
    assert "def render_sections" in sections
    assert "def _executive_summary_text" in sections
    assert "def apply_ai_draft_sections" in ai
