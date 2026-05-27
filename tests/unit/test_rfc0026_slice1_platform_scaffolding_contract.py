from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
SLICE1_PATH = Path("docs/rfcs/RFC-0026-slice-1-platform-automation-and-scaffolding-review.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice1_is_indexed_and_non_claiming() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-1-platform-automation-and-scaffolding-review.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice1 = _read(SLICE1_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "NO PLATFORM CHANGE REQUIRED BEFORE COCKPIT DOMAIN WORK" in slice1
    assert "This slice does not implement advisor cockpit APIs" in slice1
    assert "Those remain mandatory RFC-0026 work in subsequent slices" in slice1
    assert "Slice 1 is complete as platform-scaffolding review only" in flat_supported
    assert "No runtime advisor-cockpit support claim is promoted" in flat_supported


def test_rfc0026_slice1_reuses_platform_controls_without_premature_scaffolding() -> None:
    slice1 = _flat(SLICE1_PATH)

    required_controls = (
        "API certification and Swagger/OpenAPI quality gates",
        "API vocabulary and no-alias governance",
        "cursor-pagination vocabulary and existing paginated API examples",
        "domain-data-product onboarding, trust telemetry, SLO, access, evidence policy",
        "canonical front-office runtime proof routing for subsequent Gateway/Workbench",
        "heartbeat and async-monitoring guidance",
        "Sync-RepoWikis.ps1",
    )
    for control in required_controls:
        assert control in slice1

    rejected_scaffolds = (
        "a `lotus-advise`-only cockpit certification CLI",
        "a local cockpit proof-pack schema",
        "a platform-wide generic action-item framework",
        "a cockpit-specific platform canonical data contract",
        "a Workbench live proof module before Gateway-backed cockpit APIs exist",
        "local wiki publication scripts outside `Sync-RepoWikis.ps1`",
    )
    for rejected in rejected_scaffolds:
        assert rejected in slice1


def test_rfc0026_slice1_pins_subsequent_cockpit_controls_and_automation_gate() -> None:
    slice1 = _flat(SLICE1_PATH)

    subsequent_controls = (
        "Subsequent RFC-0026 slice need",
        "Dedicated cockpit domain, source-read-model, priority, SLA, acknowledgement",
        "default page size, maximum page size, invalid cursor, next cursor, stable ordering",
        "priority, status, owner role, source family, dependency family, and SLA aging band",
        "`AdvisorCockpitOperatingSnapshot:v1` and `AdvisoryActionItemRegister:v1`",
        "Platform canonical contract/invariant updates",
        "Workbench `advisor-cockpit-proof.mjs`",
        "`npm run live:stack:up:validate` proof",
        "lowest-useful-layer regression tests for every live defect",
        "no UI-local priority or workflow inference",
        "RFC-0028 full demo/RFP claims",
    )
    for control in subsequent_controls:
        assert control in slice1
