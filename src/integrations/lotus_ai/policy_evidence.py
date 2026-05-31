from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from src.integrations.lotus_ai.runtime_config import resolve_lotus_ai_base_url
from src.integrations.lotus_core.runtime_config import env_positive_float

ADAPTER_VERSION = "policy-evidence-lotus-ai-adapter.v1"
WORKFLOW_PACK_ID = "policy_evidence_summary.pack"
WORKFLOW_PACK_VERSION = "v1"
WORKFLOW_SURFACE = "policy-evidence-summary"


class LotusAIPolicyEvidenceUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class PolicyAiEvidenceDraft:
    status: str
    sections: tuple[dict[str, Any], ...]
    lineage: dict[str, Any]
    review_guidance: tuple[str, ...]


def generate_policy_evidence_summary_with_lotus_ai(
    *,
    policy_evidence: dict[str, Any],
    requested_actions: list[str],
    requested_by: str,
    reason: dict[str, Any],
) -> PolicyAiEvidenceDraft:
    base_url = _resolve_base_url()
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}/platform/workflow-packs/execute",
                json=_build_workflow_pack_request(
                    policy_evidence=policy_evidence,
                    requested_actions=requested_actions,
                    requested_by=requested_by,
                    reason=reason,
                ),
            )
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE") from exc

    if response.status_code == 200:
        execution = _safe_dict(payload.get("execution"))
        if execution.get("status") != "COMPLETED":
            raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
        result = _safe_dict(execution.get("result"))
        structured_output = _safe_dict(result.get("structured_output"))
        return PolicyAiEvidenceDraft(
            status=str(structured_output.get("state") or "REVIEW_REQUIRED"),
            sections=_map_sections(structured_output.get("sections")),
            lineage={
                "adapter_version": ADAPTER_VERSION,
                "workflow_pack_id": WORKFLOW_PACK_ID,
                "workflow_pack_version": WORKFLOW_PACK_VERSION,
                "workflow_surface": WORKFLOW_SURFACE,
                "workflow_run_id": _extract_workflow_run_id(payload),
                "model_version": _extract_model_version(result),
                "fallback_reason": None,
            },
            review_guidance=_map_string_list(structured_output.get("review_guidance")),
        )

    if response.status_code >= 500:
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    raise LotusAIPolicyEvidenceUnavailableError(_extract_detail(payload))


def build_policy_ai_unavailable_evidence(reason: str) -> PolicyAiEvidenceDraft:
    return PolicyAiEvidenceDraft(
        status="UNAVAILABLE",
        sections=(),
        lineage={
            "adapter_version": ADAPTER_VERSION,
            "workflow_pack_id": WORKFLOW_PACK_ID,
            "workflow_pack_version": WORKFLOW_PACK_VERSION,
            "workflow_surface": WORKFLOW_SURFACE,
            "workflow_run_id": None,
            "model_version": None,
            "fallback_reason": reason,
        },
        review_guidance=(
            "AI policy evidence is unavailable; use persisted policy evaluation and sign-off "
            "evidence only.",
            "Do not infer missing approvals, disclosures, consents, waivers, suitability, "
            "best-interest, or client-ready posture.",
        ),
    )


def _build_workflow_pack_request(
    *,
    policy_evidence: dict[str, Any],
    requested_actions: list[str],
    requested_by: str,
    reason: dict[str, Any],
) -> dict[str, object]:
    return {
        "pack_id": WORKFLOW_PACK_ID,
        "version": WORKFLOW_PACK_VERSION,
        "environment": os.getenv("LOTUS_AI_WORKFLOW_PACK_ENVIRONMENT", "DEVELOPMENT"),
        "caller_identity_class": "INTERNAL_SERVICE",
        "workflow_surface": WORKFLOW_SURFACE,
        "task_request": {
            "task_id": "explain_policy_evidence.v1",
            "input_mode": "STRUCTURED_CONTEXT",
            "caller": {
                "caller_app": "lotus-advise",
                "correlation_id": (f"policy-evidence-{policy_evidence.get('evaluation_id')}"),
                "requested_by": requested_by,
            },
            "context": {
                "summary": "Draft review-gated policy evidence explanation.",
                "payload": {
                    "policy_evidence": policy_evidence,
                    "policy_evidence_request": {
                        "requested_actions": requested_actions,
                        "requested_by": requested_by,
                        "reason": reason,
                    },
                    "supportability": {
                        "scope": "advisor_and_compliance_use_only",
                        "human_review_required": True,
                        "client_ready_publication": "BLOCKED",
                        "authoritative_for_policy_status": False,
                        "unsupported_claims": [
                            "client_ready_policy_publication",
                            "policy_status_mutation",
                            "rule_result_mutation",
                            "approval_or_waiver_creation",
                            "disclosure_or_consent_mutation",
                            "missing_evidence_inference",
                        ],
                    },
                },
                "source_refs": _source_refs(policy_evidence),
            },
            "expected_output_label": "EXPLANATION_ONLY",
        },
    }


def _resolve_base_url() -> str:
    return resolve_lotus_ai_base_url(
        unavailable_error_type=LotusAIPolicyEvidenceUnavailableError,
        unavailable_message="LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE",
    )


def _resolve_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_AI_TIMEOUT_SECONDS", default=10.0))


def _source_refs(policy_evidence: dict[str, Any]) -> list[str]:
    refs = [
        f"lotus-advise:policy-evaluation:{policy_evidence.get('evaluation_id')}",
        f"lotus-advise:policy-evaluation-hash:{policy_evidence.get('evaluation_hash')}",
        f"lotus-advise:policy-pack:{policy_evidence.get('policy_pack_id')}",
    ]
    source_refs = policy_evidence.get("source_refs")
    if isinstance(source_refs, list):
        refs.extend(item for item in source_refs if isinstance(item, str))
    return refs


def _map_sections(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    sections = []
    for item in value:
        if not isinstance(item, dict):
            continue
        section_key_value = item.get("section_key")
        title_value = item.get("title")
        text_value = item.get("text")
        if not (
            isinstance(section_key_value, str)
            and isinstance(title_value, str)
            and isinstance(text_value, str)
            and section_key_value.strip()
            and title_value.strip()
            and text_value.strip()
        ):
            continue
        sections.append(
            {
                "section_key": section_key_value.strip(),
                "title": title_value.strip(),
                "text": text_value.strip(),
                "review_state": "REVIEW_REQUIRED",
            }
        )
    if not sections:
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    return tuple(sections)


def _map_string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _extract_workflow_run_id(payload: dict[str, Any]) -> str | None:
    workflow_pack_run = _safe_dict(payload.get("workflow_pack_run"))
    run_id = workflow_pack_run.get("run_id")
    return run_id.strip() if isinstance(run_id, str) and run_id.strip() else None


def _extract_model_version(result: dict[str, Any]) -> str | None:
    value = result.get("model_version")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _extract_detail(payload: dict[str, Any]) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return "LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
