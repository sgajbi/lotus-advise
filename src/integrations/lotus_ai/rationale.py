import os
from typing import Any

import httpx

from src.core.workspace.models import (
    WorkspaceAssistantEvidence,
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
    WorkspaceAssistantWorkflowPackRun,
    WorkspaceAssistantWorkflowPackRunFinding,
    WorkspaceAssistantWorkflowPackRunReviewActionRequest,
    WorkspaceAssistantWorkflowPackRunReviewActionResponse,
)

_WORKFLOW_PACK_ID = "workspace_rationale.pack"
_WORKFLOW_PACK_VERSION = "v1"
_WORKFLOW_SURFACE = "advisory-workspace-assistant"


class LotusAIRationaleUnavailableError(Exception):
    pass


def generate_workspace_rationale_with_lotus_ai(
    *,
    request: WorkspaceAssistantRequest,
    evidence: WorkspaceAssistantEvidence,
) -> WorkspaceAssistantResponse:
    base_url = _resolve_base_url()
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}/platform/workflow-packs/execute",
                json=_build_workflow_pack_request(request=request, evidence=evidence),
            )
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE") from exc

    if response.status_code == 200:
        execution = _safe_dict(payload.get("execution"))
        result = _safe_dict(execution.get("result"))
        assistant_output = result.get("message")
        if execution.get("status") != "COMPLETED":
            raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
        if not isinstance(assistant_output, str) or not assistant_output.strip():
            raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
        return WorkspaceAssistantResponse(
            assistant_output=assistant_output.strip(),
            generated_by="lotus-ai",
            evidence=evidence.model_copy(deep=True),
            workflow_pack_run=_map_workflow_pack_run(_safe_dict(payload.get("workflow_pack_run"))),
        )

    detail = _extract_detail(payload)
    if response.status_code >= 500:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
    raise LotusAIRationaleUnavailableError(detail)


def apply_workspace_rationale_review_action_with_lotus_ai(
    request: WorkspaceAssistantWorkflowPackRunReviewActionRequest,
) -> WorkspaceAssistantWorkflowPackRunReviewActionResponse:
    base_url = _resolve_base_url()
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}/platform/workflow-packs/runs/{request.run_id}/review-actions",
                json=_build_review_action_request(request),
            )
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE") from exc

    if response.status_code == 200:
        workflow_pack_run = _map_workflow_pack_run(_safe_dict(payload.get("run")))
        if workflow_pack_run is None:
            raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
        return WorkspaceAssistantWorkflowPackRunReviewActionResponse(
            workflow_pack_run=workflow_pack_run,
            summary=[
                item.strip()
                for item in payload.get("summary", [])
                if isinstance(item, str) and item.strip()
            ],
        )

    detail = _extract_detail(payload)
    if response.status_code >= 500:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
    raise LotusAIRationaleUnavailableError(detail)


def _resolve_base_url() -> str:
    base_url = os.getenv("LOTUS_AI_BASE_URL", "").strip()
    if not base_url:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
    return base_url.rstrip("/")


def _resolve_timeout() -> httpx.Timeout:
    return httpx.Timeout(float(os.getenv("LOTUS_AI_TIMEOUT_SECONDS", "10.0")))


def _build_workflow_pack_request(
    *,
    request: WorkspaceAssistantRequest,
    evidence: WorkspaceAssistantEvidence,
) -> dict[str, object]:
    return {
        "pack_id": _WORKFLOW_PACK_ID,
        "version": _WORKFLOW_PACK_VERSION,
        "environment": os.getenv("LOTUS_AI_WORKFLOW_PACK_ENVIRONMENT", "DEVELOPMENT"),
        "caller_identity_class": "INTERNAL_SERVICE",
        "workflow_surface": _WORKFLOW_SURFACE,
        "task_request": {
            "task_id": "explain.v1",
            "input_mode": "STRUCTURED_CONTEXT",
            "caller": {
                "caller_app": "lotus-advise",
                "correlation_id": f"workspace-rationale-{evidence.workspace_id}",
                "requested_by": request.requested_by,
                "tenant_id": "tenant-us-002",
            },
            "context": {
                "summary": (
                    f"Advisory workspace rationale for {evidence.workspace_id} with proposal "
                    f"status {evidence.proposal_status}."
                ),
                "payload": _build_task_payload(request=request, evidence=evidence),
                "source_refs": _build_source_refs(evidence=evidence),
            },
            "expected_output_label": "EXPLANATION_ONLY",
        },
    }


def _build_task_payload(
    *,
    request: WorkspaceAssistantRequest,
    evidence: WorkspaceAssistantEvidence,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "workspace": {
            "workspace_id": evidence.workspace_id,
            "input_mode": _normalize_input_mode(evidence.input_mode),
            "requested_by": request.requested_by,
        },
        "evaluation_summary": evidence.evaluation_summary.model_dump(mode="json"),
        "proposal_status": {"value": evidence.proposal_status},
        "instruction": {"text": request.instruction},
    }
    if evidence.resolved_context is not None:
        payload["resolved_context"] = evidence.resolved_context.model_dump(mode="json")
    return payload


def _build_review_action_request(
    request: WorkspaceAssistantWorkflowPackRunReviewActionRequest,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "action_type": request.action_type,
        "caller_app": "lotus-advise",
        "reviewed_by": request.reviewed_by,
        "reason": request.reason,
    }
    if request.replacement_run_id is not None:
        payload["replacement_run_id"] = request.replacement_run_id
    return payload


def _build_source_refs(*, evidence: WorkspaceAssistantEvidence) -> list[str]:
    refs = [
        f"lotus-advise:workspace:{evidence.workspace_id}",
        f"lotus-advise:proposal-status:{evidence.proposal_status}",
        "lotus-advise:proposal-decision-summary",
    ]
    if evidence.resolved_context is not None and evidence.resolved_context.portfolio_id:
        refs.append(f"lotus-advise:portfolio:{evidence.resolved_context.portfolio_id}")
    return refs


def _extract_detail(payload: dict[str, Any]) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return "LOTUS_AI_RATIONALE_UNAVAILABLE"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_input_mode(value: Any) -> str:
    if isinstance(value, str):
        return value
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def _map_workflow_pack_run(
    payload: dict[str, Any],
) -> WorkspaceAssistantWorkflowPackRun | None:
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return None
    findings = []
    for item in payload.get("findings", []):
        if not isinstance(item, dict):
            continue
        finding_id = item.get("finding_id")
        severity = item.get("severity")
        summary = item.get("summary")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (finding_id, severity, summary)
        ):
            continue
        findings.append(
            WorkspaceAssistantWorkflowPackRunFinding(
                finding_id=finding_id,
                severity=severity,
                summary=summary,
            )
        )
    return WorkspaceAssistantWorkflowPackRun(
        run_id=run_id,
        runtime_state=str(payload.get("runtime_state", "")),
        review_state=str(payload.get("review_state", "")),
        allowed_review_actions=[
            item for item in payload.get("allowed_review_actions", []) if isinstance(item, str)
        ],
        supportability_status=str(payload.get("supportability_status", "")),
        review_pending=bool(payload.get("review_state") == "AWAITING_REVIEW"),
        superseded=bool(payload.get("supportability_status") == "HISTORICAL"),
        workflow_authority_owner=str(payload.get("workflow_authority_owner", "")),
        current_summary_note=_build_summary_note(payload),
        replacement_run_id=(
            str(payload.get("replacement_run_id"))
            if isinstance(payload.get("replacement_run_id"), str)
            else None
        ),
        findings=findings,
    )


def _build_summary_note(payload: dict[str, Any]) -> str:
    review_state = str(payload.get("review_state", ""))
    supportability_status = str(payload.get("supportability_status", ""))
    if supportability_status == "HISTORICAL":
        return "Run is historical due to replacement lineage."
    if review_state == "AWAITING_REVIEW":
        return "Run completed but still requires bounded human review before downstream use."
    if supportability_status == "READY":
        return "Run is ready for bounded downstream use."
    return "Workflow-pack run posture is available from lotus-ai."
