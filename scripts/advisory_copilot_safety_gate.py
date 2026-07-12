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

from src.core.advisory_copilot.guardrails import (  # noqa: E402
    CopilotGuardrailPolicyInput,
    CopilotGuardrailSourceEvidence,
    evaluate_copilot_guardrail_policy,
)

DEFAULT_CORPUS_PATH = Path("contracts/advisory-copilot/safety-abuse-corpus.v1.json")
DEFAULT_OUTPUT_PATH = Path("output/advisory-copilot/safety-evidence.json")
SAFETY_POLICY_VERSION = "advisory-copilot-safety-policy.v1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run advisory copilot safety-abuse gate.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    corpus = _load_json(args.corpus)
    evidence = build_safety_evidence(corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if evidence["summary"]["failed_case_count"] > 0:
        print(f"Advisory copilot safety gate failed; evidence={args.output}")
        return 1
    print(f"Advisory copilot safety gate passed; evidence={args.output}")
    return 0


def build_safety_evidence(corpus: dict[str, Any]) -> dict[str, Any]:
    _validate_corpus_header(corpus)
    results = [_evaluate_case(case) for case in _list_items(corpus.get("cases"))]
    failed = [result for result in results if not result["matched_expected_reasons"]]
    return {
        "schema_version": "lotus.advise.advisory-copilot-safety-evidence.v1",
        "dataset_id": corpus["dataset_id"],
        "dataset_hash": _stable_hash(corpus),
        "policy_version": corpus["policy_version"],
        "summary": {
            "case_count": len(results),
            "passed_case_count": len(results) - len(failed),
            "failed_case_count": len(failed),
        },
        "results": results,
    }


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    actual = evaluate_copilot_guardrail_policy(
        CopilotGuardrailPolicyInput(
            requested_intents=tuple(
                str(item) for item in _list_items(case.get("requested_intents"))
            ),
            source_evidence=_source_evidence(case.get("source_evidence")),
            user_instruction=str(case.get("user_instruction") or ""),
            model_output_sections=tuple(
                str(item) for item in _list_items(case.get("model_output_sections"))
            ),
        )
    )
    expected = tuple(str(item) for item in _list_items(case.get("expected_reason_codes")))
    return {
        "case_id": case["case_id"],
        "phase": case["phase"],
        "expected_reason_codes": list(expected),
        "actual_reason_codes": list(actual),
        "matched_expected_reasons": actual == expected,
    }


def _source_evidence(value: Any) -> tuple[CopilotGuardrailSourceEvidence, ...]:
    return tuple(
        CopilotGuardrailSourceEvidence(
            section_key=str(item.get("section_key") or ""),
            title=str(item.get("title") or ""),
            summary_items=tuple(str(text) for text in _list_items(item.get("summary_items"))),
            source_ref_count=max(int(item.get("source_ref_count") or 0), 0),
        )
        for item in _list_dicts(value)
    )


def _validate_corpus_header(corpus: dict[str, Any]) -> None:
    expected = {
        "schema_version": "lotus.advise.advisory-copilot-safety-abuse-corpus.v1",
        "dataset_id": "advisory-copilot-safety-abuse-corpus.v1",
        "policy_version": SAFETY_POLICY_VERSION,
    }
    for field, value in expected.items():
        if corpus.get(field) != value:
            raise ValueError(f"{field} must be {value}")


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in _list_items(value) if isinstance(item, dict)]


def _list_items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _stable_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
