from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

from scripts.advisory_copilot_evaluation_gate import build_evaluation_evidence
from src.core.advisory_copilot.evaluation_gate import (
    ADVISORY_COPILOT_EVALUATION_DATASET_ID,
    ADVISORY_COPILOT_EVALUATOR_VERSION,
    evaluate_advisory_copilot_model_risk,
)

CORPUS_PATH = Path("contracts/advisory-copilot/evaluation-corpus.v1.json")


def test_advisory_copilot_evaluation_gate_approves_grounded_review_output() -> None:
    result = evaluate_advisory_copilot_model_risk(
        action_family="PROPOSAL_EXPLANATION",
        workflow_pack_id="advisory_copilot_proposal_explanation.pack",
        workflow_pack_version="v1",
        provider_id="lotus-ai",
        model_version="lotus-ai-governed-model.v1",
        prompt_template_version="advisory-copilot-prompt-template.v1",
        output_schema_version="advisory-copilot-output-schema.v1",
        evaluation_pack_ref="advisory-copilot-eval-pack.v1",
        draft_status="REVIEW_REQUIRED",
        output_section_count=1,
        grounding_summary={
            "ready_for_review": True,
            "total_claims": 1,
            "grounded_claims": 1,
            "unsupported_claims": 0,
            "unverifiable_claims": 0,
        },
        guardrail_reasons=(),
    )

    assert result.approved is True
    assert result.approval_posture == "APPROVED"
    assert result.dataset_id == ADVISORY_COPILOT_EVALUATION_DATASET_ID
    assert result.evaluator_version == ADVISORY_COPILOT_EVALUATOR_VERSION
    assert result.metrics["grounded_claim_ratio_bps"] == 10000
    assert result.lineage()["evaluation_hash"].startswith("sha256:")


def test_advisory_copilot_evaluation_gate_quarantines_grounding_regression() -> None:
    result = evaluate_advisory_copilot_model_risk(
        action_family="PROPOSAL_EXPLANATION",
        workflow_pack_id="advisory_copilot_proposal_explanation.pack",
        workflow_pack_version="v1",
        provider_id="lotus-ai",
        model_version="lotus-ai-governed-model.v1",
        prompt_template_version="advisory-copilot-prompt-template.v1",
        output_schema_version="advisory-copilot-output-schema.v1",
        evaluation_pack_ref="advisory-copilot-eval-pack.v1",
        draft_status="UNSUPPORTED",
        output_section_count=1,
        grounding_summary={
            "ready_for_review": False,
            "total_claims": 1,
            "grounded_claims": 0,
            "unsupported_claims": 1,
            "unverifiable_claims": 0,
        },
        guardrail_reasons=(),
    )

    assert result.approved is False
    assert result.approval_posture == "QUARANTINED"
    assert "COPILOT_EVALUATION_GROUNDING_THRESHOLD_FAILED" in result.failure_reasons
    assert "COPILOT_EVALUATION_REVIEW_POSTURE_FAILED" in result.failure_reasons


def test_advisory_copilot_evaluation_corpus_expands_all_action_family_cases() -> None:
    corpus = _corpus()
    evidence = build_evaluation_evidence(corpus)

    assert evidence["summary"] == {
        "case_count": 36,
        "passed_case_count": 36,
        "failed_case_count": 0,
        "action_family_count": 6,
        "case_template_count": 6,
    }
    assert {result["case_type"] for result in evidence["results"]} == {
        "positive",
        "missing_evidence",
        "stale_source",
        "prompt_injection",
        "sensitive_output",
        "forbidden_intent",
    }
    assert evidence["dataset_hash"].startswith("sha256:")


def test_advisory_copilot_evaluation_corpus_fails_expected_positive_regression() -> None:
    corpus = _corpus()
    mutated = copy.deepcopy(corpus)
    positive = mutated["case_templates"][0]
    positive["grounding_summary"]["grounded_claims"] = 0
    positive["grounding_summary"]["ready_for_review"] = False
    positive["draft_status"] = "UNSUPPORTED"

    evidence = build_evaluation_evidence(mutated)

    assert evidence["summary"]["failed_case_count"] == 6
    assert all(
        result["case_type"] == "positive" and result["expected_approved"] is True
        for result in evidence["results"]
        if not result["matched_expected_posture"]
    )


def _corpus() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(CORPUS_PATH.read_text(encoding="utf-8")))
