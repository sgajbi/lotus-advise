from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE1_PATH = Path("docs/rfcs/RFC-0027-slice-1-platform-automation-and-scaffolding-review.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice1_is_indexed_and_non_claiming() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-1-platform-automation-and-scaffolding-review.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice1 = _read(SLICE1_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "NO PLATFORM CHANGE REQUIRED BEFORE COPILOT DOMAIN WORK" in slice1
    assert "This slice does not implement copilot APIs" in slice1
    assert "Those remain mandatory RFC-0027 work in subsequent slices" in slice1
    assert "Slice 1 is complete as non-promoting platform-scaffolding review" in flat_supported
    assert "before any supported copilot claim is promoted" in flat_supported


def test_rfc0027_slice1_reuses_platform_controls_without_premature_scaffolding() -> None:
    slice1 = _flat(SLICE1_PATH)

    required_controls = (
        "API certification and Swagger/OpenAPI quality gates",
        "API vocabulary and no-alias governance",
        "workflow security and GitHub action runtime validation",
        "domain-data-product onboarding, trust telemetry, SLO, access, evidence policy",
        "canonical front-office runtime proof routing for subsequent Gateway/Workbench",
        "heartbeat and async-monitoring guidance",
        "Sync-RepoWikis.ps1",
        "-AllowUnpublishedSourceChanges",
    )
    for control in required_controls:
        assert control in slice1

    rejected_scaffolds = (
        "a `lotus-advise`-only copilot certification CLI",
        "a local copilot proof-pack schema",
        "a local prompt or workflow-pack registry outside `lotus-ai`",
        "a platform-wide generic copilot framework",
        "a copilot-specific platform canonical data contract",
        "a Workbench live proof module before Gateway-backed copilot APIs exist",
        "local wiki publication scripts outside `Sync-RepoWikis.ps1`",
    )
    for rejected in rejected_scaffolds:
        assert rejected in slice1


def test_rfc0027_slice1_pins_later_copilot_controls_and_automation_gate() -> None:
    slice1 = _flat(SLICE1_PATH)

    subsequent_controls = (
        "Subsequent RFC-0027 slice need",
        "Dedicated copilot catalog, evidence-packet, guardrail, workflow-pack adapter",
        "restricted-field exclusion tests",
        "Hostile prompt tests",
        "no direct provider calls from `lotus-advise`",
        "`AdvisoryCopilotInteractionRecord:v1`",
        "Gateway contract tests",
        "no UI-local AI, guardrail, evidence, or review-state invention",
        "Platform canonical contract/invariant updates",
        "`RFC27_ADVISORY_COPILOT_CANONICAL`",
        "`npm run live:stack:up:validate` proof",
        "lowest-useful-layer regression tests for every live defect",
        "business-facing wording must explain advisor value",
    )
    for control in subsequent_controls:
        assert control in slice1


def test_rfc0027_slice1_keeps_canonical_seed_inside_rfc_without_day2_deferral() -> None:
    slice1 = _flat(SLICE1_PATH)

    assert "That is RFC-0027 Slice 12 work, not day-2 or wave-2 deferral" in slice1
    assert "canonical RFC-0027 seed data" in slice1
    assert "remain mandatory subsequent RFC-0027 work and are unpromoted in this slice" in slice1
