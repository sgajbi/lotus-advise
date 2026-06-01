from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.advisory_copilot.idempotency_records import AdvisoryCopilotRunIdempotencyRecord
from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.persistence_results import AdvisoryCopilotRunPersistenceResult
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.request_hashing import (
    build_advisory_copilot_run_request_summary,
    canonical_json_hash,
)
from src.core.advisory_copilot.retention_policy import retention_expires_at
from src.core.advisory_copilot.run_lineage import (
    DEFAULT_CALLER_APP,
    DEFAULT_EVALUATION_PACK_REF,
    DEFAULT_OUTPUT_SCHEMA_VERSION,
    DEFAULT_PROMPT_TEMPLATE_VERSION,
    DEFAULT_TENANT_ID,
    optional_lineage_text,
    stable_copilot_record_id,
)
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.run_review_policy import (
    can_refresh_retryable_copilot_run,
    review_posture_from_draft_status,
)
from src.core.advisory_copilot.structured_payload import assert_safe_structured_payload
from src.core.advisory_copilot.type_models import CopilotAudience
from src.core.advisory_copilot.workflow_pack import (
    workflow_pack_id_for_action,
    workflow_pack_version_for_action,
)
from src.core.common.idempotency import normalize_optional_idempotency_key


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
    assert_safe_structured_payload(reason)
    assert_safe_structured_payload(lineage)
    for section in output_sections:
        assert_safe_structured_payload(section)

    now = created_at or datetime.now(timezone.utc)
    request_summary = build_advisory_copilot_run_request_summary(
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

    review_posture = review_posture_from_draft_status(draft_status)
    output_json = [dict(section) for section in output_sections]
    run_id = stable_copilot_record_id(prefix="copilot_run", value=request_hash)
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
        lotus_ai_workflow_run_id=optional_lineage_text(lineage.get("workflow_run_id")),
        lotus_ai_model_version=optional_lineage_text(lineage.get("model_version")),
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
        if can_refresh_retryable_copilot_run(
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
