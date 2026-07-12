from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.advisory_copilot.evaluation_gate import (  # noqa: E402
    ADVISORY_COPILOT_EVALUATION_DATASET_ID,
    ADVISORY_COPILOT_EVALUATOR_VERSION,
    AdvisoryCopilotEvaluationThresholds,
    evaluate_advisory_copilot_model_risk,
)
from src.core.advisory_copilot.model_governance import (  # noqa: E402
    ADVISORY_COPILOT_APPROVED_MODEL_VERSION,
    ADVISORY_COPILOT_APPROVED_PROVIDER_ID,
    ADVISORY_COPILOT_EVALUATION_PACK_REF,
    ADVISORY_COPILOT_OUTPUT_SCHEMA_VERSION,
    ADVISORY_COPILOT_PROMPT_TEMPLATE_VERSION,
)
from src.core.advisory_copilot.type_models import CopilotActionFamily  # noqa: E402

DEFAULT_CORPUS_PATH = Path("contracts/advisory-copilot/evaluation-corpus.v1.json")
DEFAULT_OUTPUT_PATH = Path("output/advisory-copilot/evaluation-evidence.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run advisory copilot model-risk evaluation gate.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    corpus = _load_json(args.corpus)
    evidence = build_evaluation_evidence(corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if evidence["summary"]["failed_case_count"] > 0:
        print(f"Advisory copilot evaluation gate failed; evidence={args.output}")
        return 1
    print(f"Advisory copilot evaluation gate passed; evidence={args.output}")
    return 0


def build_evaluation_evidence(corpus: dict[str, Any]) -> dict[str, Any]:
    _validate_corpus_header(corpus)
    thresholds = _thresholds(corpus.get("thresholds", {}))
    results = [
        _evaluate_case(action=action, template=template, thresholds=thresholds)
        for action in _list_items(corpus.get("action_families"))
        for template in _list_items(corpus.get("case_templates"))
    ]
    failed = [result for result in results if not result["matched_expected_posture"]]
    return {
        "schema_version": "lotus.advise.advisory-copilot-evaluation-evidence.v1",
        "dataset_id": corpus["dataset_id"],
        "dataset_hash": _stable_hash(corpus),
        "evaluation_pack_ref": corpus["evaluation_pack_ref"],
        "evaluator_version": corpus["evaluator_version"],
        "thresholds": thresholds.as_dict(),
        "summary": {
            "case_count": len(results),
            "passed_case_count": len(results) - len(failed),
            "failed_case_count": len(failed),
            "action_family_count": len(_list_items(corpus.get("action_families"))),
            "case_template_count": len(_list_items(corpus.get("case_templates"))),
        },
        "results": results,
    }


def _evaluate_case(
    *,
    action: dict[str, Any],
    template: dict[str, Any],
    thresholds: AdvisoryCopilotEvaluationThresholds,
) -> dict[str, Any]:
    result = evaluate_advisory_copilot_model_risk(
        action_family=_action_family(action),
        workflow_pack_id=str(action["workflow_pack_id"]),
        workflow_pack_version=str(action["workflow_pack_version"]),
        provider_id=ADVISORY_COPILOT_APPROVED_PROVIDER_ID,
        model_version=ADVISORY_COPILOT_APPROVED_MODEL_VERSION,
        prompt_template_version=ADVISORY_COPILOT_PROMPT_TEMPLATE_VERSION,
        output_schema_version=ADVISORY_COPILOT_OUTPUT_SCHEMA_VERSION,
        evaluation_pack_ref=ADVISORY_COPILOT_EVALUATION_PACK_REF,
        draft_status=str(template["draft_status"]),
        output_section_count=int(template["output_section_count"]),
        grounding_summary=dict(template["grounding_summary"]),
        guardrail_reasons=tuple(str(item) for item in _list_items(template["guardrail_reasons"])),
        thresholds=thresholds,
    )
    expected_approved = bool(template["expected_approved"])
    return {
        "case_id": f"{action['action_family']}:{template['case_type']}",
        "action_family": action["action_family"],
        "case_type": template["case_type"],
        "expected_approved": expected_approved,
        "actual_approved": result.approved,
        "matched_expected_posture": result.approved is expected_approved,
        "approval_posture": result.approval_posture,
        "evaluation_hash": result.evaluation_hash,
        "metrics": result.metrics,
        "failure_reasons": list(result.failure_reasons),
    }


def _validate_corpus_header(corpus: dict[str, Any]) -> None:
    expected = {
        "schema_version": "lotus.advise.advisory-copilot-evaluation-corpus.v1",
        "dataset_id": ADVISORY_COPILOT_EVALUATION_DATASET_ID,
        "evaluation_pack_ref": ADVISORY_COPILOT_EVALUATION_PACK_REF,
        "evaluator_version": ADVISORY_COPILOT_EVALUATOR_VERSION,
    }
    for field, value in expected.items():
        if corpus.get(field) != value:
            raise ValueError(f"{field} must be {value}")


def _thresholds(value: Any) -> AdvisoryCopilotEvaluationThresholds:
    payload = dict(value) if isinstance(value, dict) else {}
    return AdvisoryCopilotEvaluationThresholds(
        min_grounded_claim_ratio_bps=int(payload.get("min_grounded_claim_ratio_bps", 10000)),
        max_guardrail_reason_count=int(payload.get("max_guardrail_reason_count", 0)),
        require_review_ready=bool(payload.get("require_review_ready", True)),
        require_output_sections=bool(payload.get("require_output_sections", True)),
    )


def _action_family(action: dict[str, Any]) -> CopilotActionFamily:
    return action["action_family"]


def _list_items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _stable_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
