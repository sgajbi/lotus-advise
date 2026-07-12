from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

from scripts.advisory_copilot_safety_gate import build_safety_evidence

CORPUS_PATH = Path("contracts/advisory-copilot/safety-abuse-corpus.v1.json")


def test_advisory_copilot_safety_corpus_matches_expected_guardrail_posture() -> None:
    evidence = build_safety_evidence(_corpus())

    assert evidence["summary"] == {
        "case_count": 6,
        "passed_case_count": 6,
        "failed_case_count": 0,
    }
    assert {result["phase"] for result in evidence["results"]} == {"PREFLIGHT", "POSTFLIGHT"}
    assert evidence["dataset_hash"].startswith("sha256:")


def test_advisory_copilot_safety_corpus_fails_when_expected_posture_drifts() -> None:
    mutated = copy.deepcopy(_corpus())
    mutated["cases"][0]["expected_reason_codes"] = []

    evidence = build_safety_evidence(mutated)

    assert evidence["summary"]["failed_case_count"] == 1
    assert evidence["results"][0]["case_id"] == "preflight:missing-source-evidence"
    assert evidence["results"][0]["matched_expected_reasons"] is False


def _corpus() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(CORPUS_PATH.read_text(encoding="utf-8")))
