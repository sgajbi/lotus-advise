from __future__ import annotations

from pathlib import Path

RFC23_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
RFC24_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
RFC25_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
AUDIT_PATH = Path("docs/rfcs/RFC-0023-0025-gold-pass-audit.md")
WTBD_PATH = Path("docs/rfcs/WTBD.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc23_24_25_gold_pass_sections_are_present_and_bounded() -> None:
    expected = {
        RFC23_PATH: (
            "Gold-Pass Assessment",
            "advisor-review proposal narrative evidence",
            "proposal-narrative-posture-live.png",
            "client-ready narrative publication",
        ),
        RFC24_PATH: (
            "Gold-Pass Assessment",
            "advisor-use proposal memo and evidence-pack support",
            "proposal-memo-evidence-pack-live.png",
            "client-ready memo publication",
        ),
        RFC25_PATH: (
            "Gold-Pass Assessment",
            "advisor/compliance policy-evidence slice",
            "POLICY_EVALUATION_PENDING_REVIEW_CREATED",
            "completed approval/sign-off/client-ready authority",
        ),
    }

    for path, required_markers in expected.items():
        text = _flat(path)
        for marker in required_markers:
            assert marker in text
        assert "remain gated" in text
        assert "no active WTBD dependency" in text


def test_consolidated_gold_pass_audit_records_live_stack_and_gated_claims() -> None:
    audit = _flat(AUDIT_PATH)

    required_markers = (
        "RFC23_25_ADVISORY_PROPOSAL_POLICY_CANONICAL",
        "PB_SG_GLOBAL_BAL_001",
        "POLICY_EVALUATION_PENDING_REVIEW_CREATED",
        "proposal-narrative-posture-live.png",
        "proposal-memo-evidence-pack-live.png",
        "advisory-suitability-review-live.png",
        "POLICY_PACK_VERSION_ALREADY_ACTIVE_IMMUTABLE",
        "client-ready narrative publication",
        "client-ready memo publication",
        "completed policy approval or waiver authority",
        "completed compliance sign-off authority",
        "full RFC-0028 bank-demo/RFP package claims",
        "npm run live:validate",
        "npm run live:stack:down",
    )
    for marker in required_markers:
        assert marker in audit


def test_wtbd_ledger_remains_closed_historical_context_only() -> None:
    wtbd = _flat(WTBD_PATH)
    audit = _flat(AUDIT_PATH)

    assert "Status: closed historical ledger." in _read(WTBD_PATH)
    for wtbd_id in ("WTBD-001", "WTBD-002", "WTBD-003", "WTBD-004"):
        assert wtbd_id in wtbd
        assert wtbd_id in audit
    assert "No active WTBD dependency remains" in audit
    assert "No new WTBD entries should be added" in _read(WTBD_PATH)
