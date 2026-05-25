from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RFC_PATH = (
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rfc0023_main_rfc_is_marked_implemented_for_bounded_posture() -> None:
    rfc_text = _read(RFC_PATH)
    rfc_index = _read("docs/rfcs/README.md")
    supported = _read("wiki/Supported-Features.md")

    assert (
        "**Status** | IMPLEMENTED for advisor-review narrative evidence; "
        "client-ready publication remains gated"
    ) in rfc_text
    assert "DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN" not in rfc_text
    assert "IMPLEMENTED for advisor-review narrative evidence" in rfc_index
    assert "Advisor-review proposal narrative | Supported" in supported
    assert "Client-ready proposal commentary | Supported" not in supported


def test_rfc0023_open_questions_are_resolved_with_closure_answers() -> None:
    rfc_text = _read(RFC_PATH)

    assert "## Resolved Slice 3 Questions" in rfc_text
    assert "## Open Questions Before Implementation" not in rfc_text
    assert "| Question | Closure answer |" in rfc_text
    assert "The first supported posture is advisor-review narrative evidence only" in rfc_text
    assert "Client-ready export remains gated" in rfc_text
    assert "Canonical `PB_SG_GLOBAL_BAL_001` Workbench proof" in rfc_text


def test_rfc0023_internal_ledger_matches_current_supported_boundary() -> None:
    rfc_text = _read(RFC_PATH)

    assert (
        "| Narrative evidence data product | Supported for advisor-review evidence |"
    ) in rfc_text
    assert (
        "| Sales/demo-safe narrative proof | Supported for advisor-review walkthrough material |"
    ) in rfc_text
    assert (
        "| Client-ready narrative | Gated | Remains gated until RFC-0028 or another approved "
        "client-ready implementation RFC proves"
    ) in rfc_text
    assert "client-ready publication remains gated" in rfc_text
