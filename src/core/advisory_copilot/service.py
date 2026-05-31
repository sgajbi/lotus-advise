from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from pydantic import BaseModel, Field

from src.core.advisory_copilot.models import (
    CopilotAudience,
    CopilotEvidencePacket,
    CopilotReviewPosture,
)
from src.core.advisory_copilot.records import (
    AdvisoryCopilotEvidencePacketRecord,
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunIdempotencyRecord,
    AdvisoryCopilotRunRecord,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.review import (
    CopilotReviewAction,
    is_terminal_review_posture,
    review_posture_for_action,
)
from src.core.advisory_copilot.workflow_pack import (
    workflow_pack_id_for_action,
    workflow_pack_version_for_action,
)
from src.core.common.idempotency import normalize_optional_idempotency_key

RAW_AI_STORAGE_KEYS = frozenset(
    {
        "prompt",
        "raw_prompt",
        "raw_output",
        "unsafe_output",
        "provider_response",
        "model_response",
        "instruction",
        "system_instruction",
    }
)

DEFAULT_CALLER_APP = "lotus-advise"
DEFAULT_TENANT_ID = "tenant-sg-001"
DEFAULT_PROMPT_TEMPLATE_VERSION = "advisory-copilot-prompt-template.v1"
DEFAULT_OUTPUT_SCHEMA_VERSION = "advisory-copilot-output-schema.v1"
DEFAULT_EVALUATION_PACK_REF = "advisory-copilot-eval-pack.v1"


class AdvisoryCopilotRunPersistenceResult(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(
        description="Persisted or replayed advisory copilot run record."
    )
    replayed: bool = Field(description="Whether the request replayed an existing idempotent run.")


class AdvisoryCopilotReviewResult(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Run after review processing.")
    review: AdvisoryCopilotReviewRecord = Field(
        description="Persisted or replayed advisory copilot review event."
    )
    replayed: bool = Field(
        description="Whether the request replayed an existing idempotent review."
    )


def save_advisory_copilot_evidence_packet(
    *,
    repository: AdvisoryCopilotRepository,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    created_by: str,
    reason: dict[str, Any],
    correlation_id: str,
    created_at: datetime | None = None,
) -> AdvisoryCopilotEvidencePacketRecord:
    _assert_safe_structured_payload(reason)
    record = AdvisoryCopilotEvidencePacketRecord(
        evidence_packet_id=evidence_packet.evidence_packet_id,
        evidence_packet_hash=evidence_packet.evidence_packet_hash,
        action_family=evidence_packet.action_family,
        audience=audience,
        portfolio_id=evidence_packet.portfolio_id,
        proposal_id=evidence_packet.proposal_id,
        created_by=created_by,
        created_at=created_at or datetime.now(timezone.utc),
        correlation_id=correlation_id,
        packet_json=evidence_packet.model_dump(mode="json"),
        reason_json=dict(reason),
    )
    return repository.save_evidence_packet(record)


def load_advisory_copilot_evidence_packet(
    *, repository: AdvisoryCopilotRepository, evidence_packet_id: str
) -> CopilotEvidencePacket:
    record = repository.get_evidence_packet(evidence_packet_id=evidence_packet_id)
    if record is None:
        raise ValueError("COPILOT_EVIDENCE_PACKET_NOT_FOUND")
    return cast(CopilotEvidencePacket, CopilotEvidencePacket.model_validate(record.packet_json))


def persist_advisory_copilot_run(
    *,
    repository: AdvisoryCopilotRepository,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: tuple[str, ...],
    requested_by: str,
    reason: dict[str, Any],
    draft_status: str,
    output_sections: tuple[dict[str, Any], ...],
    lineage: dict[str, Any],
    review_guidance: tuple[str, ...],
    guardrail_reasons: tuple[str, ...],
    correlation_id: str,
    idempotency_key: str | None = None,
    caller_app: str = DEFAULT_CALLER_APP,
    tenant_id: str = DEFAULT_TENANT_ID,
    requested_intents: tuple[str, ...] = (),
    user_instruction: str = "",
    created_at: datetime | None = None,
) -> AdvisoryCopilotRunPersistenceResult:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    _assert_safe_structured_payload(reason)
    _assert_safe_structured_payload(lineage)
    for section in output_sections:
        _assert_safe_structured_payload(section)

    now = created_at or datetime.now(timezone.utc)
    request_summary = _safe_run_request_summary(
        evidence_packet=evidence_packet,
        audience=audience,
        requested_outputs=requested_outputs,
        requested_by=requested_by,
        reason=reason,
        requested_intents=requested_intents,
        user_instruction=user_instruction,
    )
    request_hash = canonical_json_hash(request_summary)
    existing_run: AdvisoryCopilotRunRecord | None = None
    if idempotency_key:
        existing_idempotency = repository.get_run_idempotency(idempotency_key=idempotency_key)
        if existing_idempotency is not None:
            if existing_idempotency.request_hash != request_hash:
                raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
            existing_run = repository.get_run(run_id=existing_idempotency.run_id)
            if existing_run is None:
                raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")

    review_posture = _review_posture_from_draft(draft_status)
    output_json = [dict(section) for section in output_sections]
    run_id = _stable_id(prefix="copilot_run", value=request_hash)
    run = AdvisoryCopilotRunRecord(
        run_id=run_id,
        action_family=evidence_packet.action_family,
        audience=audience,
        portfolio_id=evidence_packet.portfolio_id,
        proposal_id=evidence_packet.proposal_id,
        evidence_packet_id=evidence_packet.evidence_packet_id,
        evidence_packet_hash=evidence_packet.evidence_packet_hash,
        request_hash=request_hash,
        output_hash=canonical_json_hash(output_json),
        review_posture=review_posture,
        client_ready_publication=evidence_packet.client_ready_publication,
        retention_class=evidence_packet.retention_class,
        retention_expires_at=retention_expires_at(
            retention_class=evidence_packet.retention_class,
            created_at=now,
        ),
        created_by=requested_by,
        caller_app=caller_app,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
        lotus_ai_workflow_run_id=_optional_str(lineage.get("workflow_run_id")),
        lotus_ai_model_version=_optional_str(lineage.get("model_version")),
        workflow_pack_id=str(
            lineage.get("workflow_pack_id")
            or workflow_pack_id_for_action(evidence_packet.action_family)
        ),
        workflow_pack_version=str(
            lineage.get("workflow_pack_version")
            or workflow_pack_version_for_action(evidence_packet.action_family)
        ),
        prompt_template_version=str(
            lineage.get("prompt_template_version") or DEFAULT_PROMPT_TEMPLATE_VERSION
        ),
        output_schema_version=str(
            lineage.get("output_schema_version") or DEFAULT_OUTPUT_SCHEMA_VERSION
        ),
        evaluation_pack_ref=str(lineage.get("evaluation_pack_ref") or DEFAULT_EVALUATION_PACK_REF),
        evidence_packet_json=evidence_packet.model_dump(mode="json"),
        request_summary_json=request_summary,
        output_sections_json=output_json,
        review_guidance_json=list(review_guidance),
        guardrail_results_json=list(guardrail_reasons),
        lineage_json=dict(lineage),
    )
    if existing_run is not None:
        if _can_refresh_retryable_run(
            existing_run=existing_run,
            incoming_review_posture=review_posture,
        ):
            refreshed_run = run.model_copy(
                update={
                    "run_id": existing_run.run_id,
                    "created_at": existing_run.created_at,
                    "idempotency_key": existing_run.idempotency_key,
                    "legal_hold": existing_run.legal_hold,
                }
            )
            repository.update_run(refreshed_run)
            return AdvisoryCopilotRunPersistenceResult(run=refreshed_run, replayed=False)
        return AdvisoryCopilotRunPersistenceResult(run=existing_run, replayed=True)

    idempotency = (
        AdvisoryCopilotRunIdempotencyRecord(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            run_id=run.run_id,
            created_at=now,
        )
        if idempotency_key
        else None
    )
    saved_run = repository.save_run_with_idempotency(run=run, idempotency=idempotency)
    return AdvisoryCopilotRunPersistenceResult(run=saved_run, replayed=False)


def build_advisory_copilot_run_request_hash(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: tuple[str, ...],
    requested_by: str,
    reason: dict[str, Any],
    requested_intents: tuple[str, ...],
    user_instruction: str,
) -> str:
    _assert_safe_structured_payload(reason)
    return canonical_json_hash(
        _safe_run_request_summary(
            evidence_packet=evidence_packet,
            audience=audience,
            requested_outputs=requested_outputs,
            requested_by=requested_by,
            reason=reason,
            requested_intents=requested_intents,
            user_instruction=user_instruction,
        )
    )


def record_advisory_copilot_review(
    *,
    repository: AdvisoryCopilotRepository,
    run_id: str,
    action: CopilotReviewAction,
    actor_id: str,
    reason: dict[str, Any],
    correlation_id: str,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
) -> AdvisoryCopilotReviewResult:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    _assert_safe_structured_payload(reason)
    run = repository.get_run(run_id=run_id)
    if run is None:
        raise ValueError("COPILOT_RUN_NOT_FOUND")

    now = occurred_at or datetime.now(timezone.utc)
    review_request = {
        "run_id": run_id,
        "action": action,
        "actor_id": actor_id,
        "reason": reason,
    }
    request_hash = canonical_json_hash(review_request)
    if idempotency_key:
        existing_review = repository.get_review_by_idempotency(
            run_id=run_id,
            idempotency_key=idempotency_key,
        )
        if existing_review is not None:
            if existing_review.request_hash != request_hash:
                raise ValueError("COPILOT_REVIEW_IDEMPOTENCY_KEY_CONFLICT")
            replayed_run = repository.get_run(run_id=run_id)
            if replayed_run is None:
                raise ValueError("COPILOT_REVIEW_RECORD_ORPHANED")
            return AdvisoryCopilotReviewResult(
                run=replayed_run,
                review=existing_review,
                replayed=True,
            )

    if is_terminal_review_posture(run.review_posture):
        raise ValueError("COPILOT_RUN_REVIEW_POSTURE_TERMINAL")

    new_posture = review_posture_for_action(action)
    review = AdvisoryCopilotReviewRecord(
        review_id=_stable_id(prefix="copilot_review", value=request_hash),
        run_id=run_id,
        action=action,
        previous_posture=run.review_posture,
        new_posture=new_posture,
        actor_id=actor_id,
        occurred_at=now,
        reason_json=dict(reason),
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    updated_run = run.model_copy(update={"review_posture": new_posture, "updated_at": now})
    repository.append_review(review)
    repository.update_run(updated_run)
    return AdvisoryCopilotReviewResult(run=updated_run, review=review, replayed=False)


def list_advisory_copilot_reviews(
    *, repository: AdvisoryCopilotRepository, run_id: str
) -> tuple[AdvisoryCopilotReviewRecord, ...]:
    return tuple(repository.list_reviews(run_id=run_id))


def canonical_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def retention_expires_at(*, retention_class: str, created_at: datetime) -> datetime:
    if retention_class == "SUPPORTABILITY_DIAGNOSTIC":
        return created_at + timedelta(days=90)
    return created_at + timedelta(days=365 * 7)


def _safe_run_request_summary(
    *,
    evidence_packet: CopilotEvidencePacket,
    audience: CopilotAudience,
    requested_outputs: tuple[str, ...],
    requested_by: str,
    reason: dict[str, Any],
    requested_intents: tuple[str, ...],
    user_instruction: str,
) -> dict[str, Any]:
    return {
        "action_family": evidence_packet.action_family,
        "audience": audience,
        "portfolio_id": evidence_packet.portfolio_id,
        "proposal_id": evidence_packet.proposal_id,
        "evidence_packet_id": evidence_packet.evidence_packet_id,
        "evidence_packet_hash": evidence_packet.evidence_packet_hash,
        "requested_outputs": list(requested_outputs),
        "requested_by": requested_by,
        "reason": reason,
        "requested_intents": list(requested_intents),
        "user_instruction_hash": _optional_user_instruction_hash(user_instruction),
    }


def _optional_user_instruction_hash(value: str) -> str | None:
    stripped = value.strip()
    if not stripped:
        return None
    return canonical_json_hash({"user_instruction": stripped})


def _review_posture_from_draft(status: str) -> CopilotReviewPosture:
    allowed: set[CopilotReviewPosture] = {
        "REVIEW_REQUIRED",
        "APPROVED_FOR_INTERNAL_USE",
        "REJECTED",
        "SUPERSEDED",
        "EXPIRED",
        "UNSUPPORTED",
        "GUARDRAIL_REJECTED",
        "UNAVAILABLE",
    }
    return status if status in allowed else "REVIEW_REQUIRED"  # type: ignore[return-value]


def _can_refresh_retryable_run(
    *,
    existing_run: AdvisoryCopilotRunRecord,
    incoming_review_posture: CopilotReviewPosture,
) -> bool:
    if not can_attempt_advisory_copilot_run_refresh(existing_run):
        return False
    if existing_run.review_posture == "UNAVAILABLE" and incoming_review_posture != "UNAVAILABLE":
        return True
    return bool(
        existing_run.review_posture == "GUARDRAIL_REJECTED"
        and incoming_review_posture == "REVIEW_REQUIRED"
    )


def can_attempt_advisory_copilot_run_refresh(existing_run: AdvisoryCopilotRunRecord) -> bool:
    fallback_reason = existing_run.lineage_json.get("fallback_reason")
    if existing_run.review_posture == "UNAVAILABLE":
        return fallback_reason is not None
    return bool(
        existing_run.review_posture == "GUARDRAIL_REJECTED"
        and fallback_reason == "COPILOT_OUTPUT_GUARDRAIL_REJECTED"
    )


def _assert_safe_structured_payload(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).strip().lower() in RAW_AI_STORAGE_KEYS:
                raise ValueError("COPILOT_RAW_AI_PAYLOAD_NOT_ALLOWED")
            _assert_safe_structured_payload(nested)
    elif isinstance(value, list | tuple):
        for item in value:
            _assert_safe_structured_payload(item)


def _optional_str(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _stable_id(*, prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"
