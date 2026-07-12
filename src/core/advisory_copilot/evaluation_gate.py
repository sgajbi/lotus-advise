from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from src.core.advisory_copilot.model_governance import ADVISORY_COPILOT_EVALUATION_PACK_REF
from src.core.advisory_copilot.type_models import CopilotActionFamily

ADVISORY_COPILOT_EVALUATOR_VERSION = "advisory-copilot-evaluator.v1"
ADVISORY_COPILOT_EVALUATION_DATASET_ID = "advisory-copilot-evaluation-corpus.v1"

EvaluationApprovalPosture = Literal["APPROVED", "QUARANTINED"]
EvaluationFailureReason = Literal[
    "COPILOT_EVALUATION_PACK_MISMATCH",
    "COPILOT_EVALUATION_NO_OUTPUT_SECTIONS",
    "COPILOT_EVALUATION_GROUNDING_THRESHOLD_FAILED",
    "COPILOT_EVALUATION_GUARDRAIL_FAILED",
    "COPILOT_EVALUATION_REVIEW_POSTURE_FAILED",
]


@dataclass(frozen=True)
class AdvisoryCopilotEvaluationThresholds:
    min_grounded_claim_ratio_bps: int = 10000
    max_guardrail_reason_count: int = 0
    require_review_ready: bool = True
    require_output_sections: bool = True

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "min_grounded_claim_ratio_bps": self.min_grounded_claim_ratio_bps,
            "max_guardrail_reason_count": self.max_guardrail_reason_count,
            "require_review_ready": self.require_review_ready,
            "require_output_sections": self.require_output_sections,
        }


@dataclass(frozen=True)
class AdvisoryCopilotEvaluationResult:
    approved: bool
    approval_posture: EvaluationApprovalPosture
    evaluation_pack_ref: str
    evaluator_version: str
    dataset_id: str
    evaluation_hash: str
    thresholds: AdvisoryCopilotEvaluationThresholds
    metrics: dict[str, int | bool | str | None]
    failure_reasons: tuple[EvaluationFailureReason, ...]

    def lineage(self) -> dict[str, Any]:
        return {
            "approval_posture": self.approval_posture,
            "approved": self.approved,
            "evaluation_pack_ref": self.evaluation_pack_ref,
            "evaluator_version": self.evaluator_version,
            "dataset_id": self.dataset_id,
            "evaluation_hash": self.evaluation_hash,
            "thresholds": self.thresholds.as_dict(),
            "metrics": dict(self.metrics),
            "failure_reasons": list(self.failure_reasons),
        }


def evaluate_advisory_copilot_model_risk(
    *,
    action_family: CopilotActionFamily,
    workflow_pack_id: str,
    workflow_pack_version: str,
    provider_id: str | None,
    model_version: str | None,
    prompt_template_version: str,
    output_schema_version: str,
    evaluation_pack_ref: str,
    draft_status: str,
    output_section_count: int,
    grounding_summary: dict[str, Any],
    guardrail_reasons: tuple[str, ...],
    thresholds: AdvisoryCopilotEvaluationThresholds | None = None,
) -> AdvisoryCopilotEvaluationResult:
    thresholds = thresholds or AdvisoryCopilotEvaluationThresholds()
    metrics = _evaluation_metrics(
        draft_status=draft_status,
        output_section_count=output_section_count,
        grounding_summary=grounding_summary,
        guardrail_reasons=guardrail_reasons,
    )
    failure_reasons = _failure_reasons(
        evaluation_pack_ref=evaluation_pack_ref,
        metrics=metrics,
        thresholds=thresholds,
    )
    approved = not failure_reasons
    evidence = {
        "action_family": action_family,
        "workflow_pack_id": workflow_pack_id,
        "workflow_pack_version": workflow_pack_version,
        "provider_id": provider_id,
        "model_version": model_version,
        "prompt_template_version": prompt_template_version,
        "output_schema_version": output_schema_version,
        "evaluation_pack_ref": evaluation_pack_ref,
        "evaluator_version": ADVISORY_COPILOT_EVALUATOR_VERSION,
        "dataset_id": ADVISORY_COPILOT_EVALUATION_DATASET_ID,
        "metrics": metrics,
        "thresholds": thresholds.as_dict(),
        "failure_reasons": list(failure_reasons),
    }
    return AdvisoryCopilotEvaluationResult(
        approved=approved,
        approval_posture="APPROVED" if approved else "QUARANTINED",
        evaluation_pack_ref=evaluation_pack_ref,
        evaluator_version=ADVISORY_COPILOT_EVALUATOR_VERSION,
        dataset_id=ADVISORY_COPILOT_EVALUATION_DATASET_ID,
        evaluation_hash=_stable_hash(evidence),
        thresholds=thresholds,
        metrics=metrics,
        failure_reasons=failure_reasons,
    )


def _evaluation_metrics(
    *,
    draft_status: str,
    output_section_count: int,
    grounding_summary: dict[str, Any],
    guardrail_reasons: tuple[str, ...],
) -> dict[str, int | bool | str | None]:
    total_claims = _non_negative_int(grounding_summary.get("total_claims"))
    grounded_claims = _non_negative_int(grounding_summary.get("grounded_claims"))
    return {
        "draft_status": draft_status,
        "ready_for_review": bool(grounding_summary.get("ready_for_review")),
        "output_section_count": max(output_section_count, 0),
        "total_claims": total_claims,
        "grounded_claims": grounded_claims,
        "unsupported_claims": _non_negative_int(grounding_summary.get("unsupported_claims")),
        "unverifiable_claims": _non_negative_int(grounding_summary.get("unverifiable_claims")),
        "grounded_claim_ratio_bps": _grounded_claim_ratio_bps(
            total_claims=total_claims,
            grounded_claims=grounded_claims,
        ),
        "guardrail_reason_count": len(guardrail_reasons),
    }


def _failure_reasons(
    *,
    evaluation_pack_ref: str,
    metrics: dict[str, int | bool | str | None],
    thresholds: AdvisoryCopilotEvaluationThresholds,
) -> tuple[EvaluationFailureReason, ...]:
    failures: list[EvaluationFailureReason] = []
    if _evaluation_pack_mismatch(evaluation_pack_ref):
        failures.append("COPILOT_EVALUATION_PACK_MISMATCH")
    if _missing_output_sections(metrics=metrics, thresholds=thresholds):
        failures.append("COPILOT_EVALUATION_NO_OUTPUT_SECTIONS")
    if _grounding_threshold_failed(metrics=metrics, thresholds=thresholds):
        failures.append("COPILOT_EVALUATION_GROUNDING_THRESHOLD_FAILED")
    if _guardrail_threshold_failed(metrics=metrics, thresholds=thresholds):
        failures.append("COPILOT_EVALUATION_GUARDRAIL_FAILED")
    if _review_posture_failed(metrics=metrics, thresholds=thresholds):
        failures.append("COPILOT_EVALUATION_REVIEW_POSTURE_FAILED")
    return tuple(failures)


def _evaluation_pack_mismatch(evaluation_pack_ref: str) -> bool:
    return evaluation_pack_ref != str(ADVISORY_COPILOT_EVALUATION_PACK_REF)


def _missing_output_sections(
    *,
    metrics: dict[str, int | bool | str | None],
    thresholds: AdvisoryCopilotEvaluationThresholds,
) -> bool:
    return thresholds.require_output_sections and int(metrics["output_section_count"] or 0) <= 0


def _grounding_threshold_failed(
    *,
    metrics: dict[str, int | bool | str | None],
    thresholds: AdvisoryCopilotEvaluationThresholds,
) -> bool:
    return int(metrics["grounded_claim_ratio_bps"] or 0) < thresholds.min_grounded_claim_ratio_bps


def _guardrail_threshold_failed(
    *,
    metrics: dict[str, int | bool | str | None],
    thresholds: AdvisoryCopilotEvaluationThresholds,
) -> bool:
    return int(metrics["guardrail_reason_count"] or 0) > thresholds.max_guardrail_reason_count


def _review_posture_failed(
    *,
    metrics: dict[str, int | bool | str | None],
    thresholds: AdvisoryCopilotEvaluationThresholds,
) -> bool:
    return thresholds.require_review_ready and (
        metrics["draft_status"] != "REVIEW_REQUIRED" or metrics["ready_for_review"] is not True
    )


def _grounded_claim_ratio_bps(*, total_claims: int, grounded_claims: int) -> int:
    if total_claims <= 0:
        return 0
    return int((grounded_claims * 10000) / total_claims)


def _non_negative_int(value: Any) -> int:
    return max(int(value), 0) if isinstance(value, int) else 0


def _stable_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
