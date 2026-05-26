from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE1_PATH = Path("docs/rfcs/RFC-0025-slice-1-platform-automation-and-scaffolding-review.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice1_evidence_is_indexed_and_non_claiming() -> None:
    rfc = _read(RFC_PATH)
    slice1 = _read(SLICE1_PATH)
    rfc_index = _read(RFC_INDEX_PATH)
    wiki_index = _read(WIKI_RFC_INDEX_PATH)
    flat_wiki_index = _flat(wiki_index)

    source_ref = "docs/rfcs/RFC-0025-slice-1-platform-automation-and-scaffolding-review.md"
    assert source_ref in rfc
    assert source_ref in rfc_index
    assert source_ref in wiki_index

    assert "NO PLATFORM CHANGE REQUIRED BEFORE POLICY DOMAIN WORK" in slice1
    assert "This slice does not implement policy-pack catalog APIs" in slice1
    assert "no `lotus-platform` code change is required for this slice" in flat_wiki_index
    assert "policy-pack runtime capability is promoted" not in slice1


def test_rfc0025_slice1_reuses_platform_controls_without_local_scaffolding() -> None:
    slice1 = _read(SLICE1_PATH)
    flat_slice1 = _flat(slice1)

    required_controls = (
        "API certification and Swagger/OpenAPI quality gates",
        "API vocabulary and no-alias governance",
        "domain-data-product onboarding, trust telemetry, SLO, access, evidence policy",
        "canonical front-office runtime proof routing",
        "Feature Lane, PR Merge Gate, Main Releasability Gate",
        "Sync-RepoWikis.ps1",
    )
    for control in required_controls:
        assert control in flat_slice1

    rejected_scaffolds = (
        "a `lotus-advise`-only policy certification CLI",
        "a local policy proof-pack schema",
        "a local policy-pack registry in `lotus-platform`",
        "local wiki publication scripts outside `Sync-RepoWikis.ps1`",
    )
    for rejected in rejected_scaffolds:
        assert rejected in flat_slice1


def test_rfc0025_slice1_pins_later_policy_controls_and_source_boundaries() -> None:
    slice1 = _read(SLICE1_PATH)
    supported = _flat(_read(WIKI_SUPPORTED_FEATURES_PATH))
    flat_slice1 = _flat(slice1)

    later_controls = (
        "Dedicated policy domain, configuration, validation, evaluation, persistence, replay",
        "Owner-repo implementation where policy-critical facts are required",
        "`AdvisoryPolicyEvaluationRecord:v1` producer declaration",
        "AI workflow packs may summarize bounded policy evidence only",
        "no UI-local policy inference",
        "legal-advice non-claims",
    )
    for control in later_controls:
        assert control in flat_slice1

    assert "Slice 1 is complete as platform-scaffolding review only" in supported
    assert "no `lotus-platform` code change is required yet" in supported
    assert "no policy-pack runtime capability is promoted" in supported
    assert "Enterprise suitability and best-interest policy packs | Supported" not in supported
