from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn, cast

import httpx

from src.integrations.lotus_ai.output_safety import (
    DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH,
    DEFAULT_AI_OUTPUT_SECTION_LIMIT,
    DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH,
    DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH,
    DEFAULT_AI_REVIEW_GUIDANCE_LENGTH,
    DEFAULT_AI_REVIEW_GUIDANCE_LIMIT,
    map_bounded_string_list,
    map_review_required_sections,
)
from src.integrations.lotus_ai.runtime_config import resolve_lotus_ai_base_url
from src.integrations.lotus_ai.workflow_request import build_workflow_pack_execute_request
from src.integrations.lotus_ai.workflow_response import (
    extract_error_detail,
    extract_model_version,
    extract_workflow_run_id,
    safe_dict,
)
from src.integrations.lotus_core.runtime_config import env_positive_float

ADAPTER_VERSION = "policy-evidence-lotus-ai-adapter.v1"
WORKFLOW_PACK_ID = "policy_evidence_summary.pack"
WORKFLOW_PACK_VERSION = "v1"
WORKFLOW_SURFACE = "policy-evidence-summary"
MAX_POLICY_AI_OUTPUT_SECTIONS = DEFAULT_AI_OUTPUT_SECTION_LIMIT
MAX_POLICY_AI_SECTION_KEY_LENGTH = DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH
MAX_POLICY_AI_SECTION_TITLE_LENGTH = DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH
MAX_POLICY_AI_SECTION_TEXT_LENGTH = DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH
MAX_POLICY_AI_REVIEW_GUIDANCE_ITEMS = DEFAULT_AI_REVIEW_GUIDANCE_LIMIT
MAX_POLICY_AI_REVIEW_GUIDANCE_LENGTH = DEFAULT_AI_REVIEW_GUIDANCE_LENGTH


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
    response, payload = _post_workflow_pack_request(
        base_url=base_url,
        request_payload=_build_workflow_pack_request(
            policy_evidence=policy_evidence,
            requested_actions=requested_actions,
            requested_by=requested_by,
            reason=reason,
        ),
    )

    if response.status_code == 200:
        return _policy_evidence_summary_from_success(payload)

    _raise_policy_evidence_response_error(response.status_code, payload)


def _post_workflow_pack_request(
    *,
    base_url: str,
    request_payload: dict[str, object],
) -> tuple[httpx.Response, dict[str, Any]]:
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}/platform/workflow-packs/execute",
                json=request_payload,
            )
            payload = safe_dict(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE") from exc
    return response, payload


def _policy_evidence_summary_from_success(
    payload: dict[str, Any],
) -> PolicyAiEvidenceDraft:
    execution = safe_dict(payload.get("execution"))
    if execution.get("status") != "COMPLETED":
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    result = safe_dict(execution.get("result"))
    structured_output = safe_dict(result.get("structured_output"))
    return PolicyAiEvidenceDraft(
        status=str(structured_output.get("state") or "REVIEW_REQUIRED"),
        sections=_map_sections(structured_output.get("sections")),
        lineage={
            "adapter_version": ADAPTER_VERSION,
            "workflow_pack_id": WORKFLOW_PACK_ID,
            "workflow_pack_version": WORKFLOW_PACK_VERSION,
            "workflow_surface": WORKFLOW_SURFACE,
            "workflow_run_id": extract_workflow_run_id(payload),
            "model_version": extract_model_version(result),
            "fallback_reason": None,
        },
        review_guidance=_map_string_list(structured_output.get("review_guidance")),
    )


def _raise_policy_evidence_response_error(
    status_code: int,
    payload: dict[str, Any],
) -> NoReturn:
    if status_code >= 500:
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    raise LotusAIPolicyEvidenceUnavailableError(
        extract_error_detail(payload, default="LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    )


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
    return build_workflow_pack_execute_request(
        pack_id=WORKFLOW_PACK_ID,
        version=WORKFLOW_PACK_VERSION,
        workflow_surface=WORKFLOW_SURFACE,
        task_id="explain_policy_evidence.v1",
        correlation_id=f"policy-evidence-{policy_evidence.get('evaluation_id')}",
        requested_by=requested_by,
        context_summary="Draft review-gated policy evidence explanation.",
        context_payload={
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
        source_refs=_source_refs(policy_evidence),
        expected_output_label="EXPLANATION_ONLY",
    )


def _resolve_base_url() -> str:
    return cast(
        str,
        resolve_lotus_ai_base_url(
            unavailable_error_type=LotusAIPolicyEvidenceUnavailableError,
            unavailable_message="LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE",
        ),
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
    sections = map_review_required_sections(
        value,
        max_sections=MAX_POLICY_AI_OUTPUT_SECTIONS,
        max_section_key_length=MAX_POLICY_AI_SECTION_KEY_LENGTH,
        max_title_length=MAX_POLICY_AI_SECTION_TITLE_LENGTH,
        max_text_length=MAX_POLICY_AI_SECTION_TEXT_LENGTH,
    )
    if not sections:
        raise LotusAIPolicyEvidenceUnavailableError("LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE")
    return sections


def _map_string_list(value: Any) -> tuple[str, ...]:
    return map_bounded_string_list(
        value,
        max_items=MAX_POLICY_AI_REVIEW_GUIDANCE_ITEMS,
        max_item_length=MAX_POLICY_AI_REVIEW_GUIDANCE_LENGTH,
    )
