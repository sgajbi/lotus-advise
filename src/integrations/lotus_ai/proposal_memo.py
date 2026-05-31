from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, cast

import httpx

from src.integrations.lotus_ai.runtime_config import (
    resolve_lotus_ai_base_url,
    resolve_lotus_ai_tenant_id,
)
from src.integrations.lotus_core.runtime_config import env_positive_float

ADAPTER_VERSION = "proposal-memo-commentary-lotus-ai-adapter.v1"
WORKFLOW_PACK_ID = "proposal_memo_commentary.pack"
WORKFLOW_PACK_VERSION = "v1"
WORKFLOW_SURFACE = "advisor-proposal-memo-commentary"
MAX_MEMO_AI_OUTPUT_SECTIONS = 8
MAX_MEMO_AI_SECTION_KEY_LENGTH = 96
MAX_MEMO_AI_SECTION_TITLE_LENGTH = 160
MAX_MEMO_AI_SECTION_TEXT_LENGTH = 4000
MAX_MEMO_AI_REVIEW_GUIDANCE_ITEMS = 8
MAX_MEMO_AI_REVIEW_GUIDANCE_LENGTH = 1000


class LotusAIProposalMemoUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class ProposalMemoAiCommentaryDraft:
    status: str
    sections: tuple[dict[str, Any], ...]
    lineage: dict[str, Any]
    review_guidance: tuple[str, ...]


def generate_proposal_memo_commentary_with_lotus_ai(
    *,
    memo_evidence: dict[str, Any],
    requested_sections: list[str],
    requested_by: str,
    reason: dict[str, Any],
) -> ProposalMemoAiCommentaryDraft:
    base_url = _resolve_base_url()
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}/platform/workflow-packs/execute",
                json=_build_workflow_pack_request(
                    memo_evidence=memo_evidence,
                    requested_sections=requested_sections,
                    requested_by=requested_by,
                    reason=reason,
                ),
            )
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusAIProposalMemoUnavailableError("LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE") from exc

    if response.status_code == 200:
        execution = _safe_dict(payload.get("execution"))
        if execution.get("status") != "COMPLETED":
            raise LotusAIProposalMemoUnavailableError("LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE")
        result = _safe_dict(execution.get("result"))
        structured_output = _safe_dict(result.get("structured_output"))
        return ProposalMemoAiCommentaryDraft(
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
        raise LotusAIProposalMemoUnavailableError("LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE")
    raise LotusAIProposalMemoUnavailableError(_extract_detail(payload))


def build_proposal_memo_ai_unavailable_commentary(reason: str) -> ProposalMemoAiCommentaryDraft:
    return ProposalMemoAiCommentaryDraft(
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
            "AI memo commentary is unavailable; use persisted memo evidence "
            "and deterministic sections only.",
            "Do not infer missing suitability, eligibility, fee, tax, conflict, "
            "or approval evidence.",
        ),
    )


def _build_workflow_pack_request(
    *,
    memo_evidence: dict[str, Any],
    requested_sections: list[str],
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
            "task_id": "explain.v1",
            "input_mode": "STRUCTURED_CONTEXT",
            "caller": {
                "caller_app": "lotus-advise",
                "correlation_id": f"proposal-memo-commentary-{memo_evidence.get('memo_id')}",
                "requested_by": requested_by,
                "tenant_id": resolve_lotus_ai_tenant_id(),
            },
            "context": {
                "summary": "Draft review-gated advisor-use proposal memo commentary.",
                "payload": {
                    "memo_evidence": memo_evidence,
                    "commentary_request": {
                        "requested_sections": requested_sections,
                        "requested_by": requested_by,
                        "reason": reason,
                    },
                    "supportability": {
                        "scope": "advisor_use_only",
                        "review_required": True,
                        "client_ready_publication": "BLOCKED",
                        "unsupported_claims": [
                            "client_ready_memo_publication",
                            "suitability_or_approval_mutation",
                            "missing_evidence_inference",
                        ],
                    },
                },
                "source_refs": _source_refs(memo_evidence),
            },
            "expected_output_label": "EXPLANATION_ONLY",
        },
    }


def _resolve_base_url() -> str:
    return cast(
        str,
        resolve_lotus_ai_base_url(
            unavailable_error_type=LotusAIProposalMemoUnavailableError,
            unavailable_message="LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE",
        ),
    )


def _resolve_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_AI_TIMEOUT_SECONDS", default=10.0))


def _source_refs(memo_evidence: dict[str, Any]) -> list[str]:
    refs = [
        f"lotus-advise:memo:{memo_evidence.get('memo_id')}",
        f"lotus-advise:memo_hash:{memo_evidence.get('memo_hash')}",
        f"lotus-advise:proposal:{memo_evidence.get('proposal_id')}",
    ]
    source_refs = memo_evidence.get("source_refs")
    if isinstance(source_refs, list):
        refs.extend(item for item in source_refs if isinstance(item, str))
    return refs


def _map_sections(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        raise LotusAIProposalMemoUnavailableError("LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE")
    sections: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if len(sections) >= MAX_MEMO_AI_OUTPUT_SECTIONS:
            break
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
        if (
            len(section_key_value.strip()) > MAX_MEMO_AI_SECTION_KEY_LENGTH
            or len(title_value.strip()) > MAX_MEMO_AI_SECTION_TITLE_LENGTH
            or len(text_value.strip()) > MAX_MEMO_AI_SECTION_TEXT_LENGTH
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
        raise LotusAIProposalMemoUnavailableError("LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE")
    return tuple(sections)


def _map_string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    items: list[str] = []
    for item in value:
        if len(items) >= MAX_MEMO_AI_REVIEW_GUIDANCE_ITEMS:
            break
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if not stripped or len(stripped) > MAX_MEMO_AI_REVIEW_GUIDANCE_LENGTH:
            continue
        items.append(stripped)
    return tuple(items)


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
    return "LOTUS_AI_MEMO_COMMENTARY_UNAVAILABLE"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
