from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE4_PATH = Path("docs/rfcs/RFC-0025-slice-4-upstream-source-evidence-completion.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
EVIDENCE_PATH = Path("src/core/proposals/evidence.py")
POLICY_READINESS_PATH = Path("src/core/proposals/policy_source_readiness.py")


def test_rfc0025_slice4_source_readiness_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-4-upstream-source-evidence-completion.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Source Evidence Boundary",
        "## Implementation",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    )
    for section in required_sections:
        assert section in slice4_text

    assert "IMPLEMENTED - SOURCE-READINESS ONLY" in slice4_text
    assert "`rfc0025.policy-source-readiness.v1`" in slice4_text
    assert "SOURCE_READINESS_WITH_INTERNAL_POLICY_EVALUATION_ENGINE" in slice4_text


def test_rfc0025_slice4_keeps_policy_support_unpromoted() -> None:
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    evidence_source = EVIDENCE_PATH.read_text(encoding="utf-8")
    readiness_source = POLICY_READINESS_PATH.read_text(encoding="utf-8")

    assert "This is not policy evaluation" in slice4_text
    assert "policy evaluation support is Planned" in supported_features
    assert "rfc0025.policy-source-readiness.v1" in supported_features
    assert "build_policy_source_readiness" in evidence_source
    assert "INTERNAL_ENGINE_ONLY_NO_PERSISTED_API" in readiness_source
    assert "SOURCE_READINESS_WITH_INTERNAL_POLICY_EVALUATION_ENGINE" in readiness_source
    assert '"client_ready_publication": "BLOCKED"' in readiness_source
    assert "advisory.proposals.policy_evaluation" not in readiness_source
    assert "Policy evaluation | Supported" not in supported_features
