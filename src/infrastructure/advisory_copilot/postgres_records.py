from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord


def run_values(run: AdvisoryCopilotRunRecord) -> tuple[Any, ...]:
    return (
        run.run_id,
        run.schema_version,
        run.action_family,
        run.audience,
        run.portfolio_id,
        run.proposal_id,
        run.evidence_packet_id,
        run.evidence_packet_hash,
        run.request_hash,
        run.output_hash,
        run.review_posture,
        run.client_ready_publication,
        run.retention_class,
        run.legal_hold,
        run.retention_expires_at.isoformat() if run.retention_expires_at else None,
        run.created_by,
        run.caller_app,
        run.tenant_id,
        run.correlation_id,
        run.idempotency_key,
        run.created_at.isoformat(),
        run.updated_at.isoformat(),
        run.lotus_ai_workflow_run_id,
        run.lotus_ai_model_version,
        run.workflow_pack_id,
        run.workflow_pack_version,
        run.prompt_template_version,
        run.output_schema_version,
        run.evaluation_pack_ref,
        json_dump(run.evidence_packet_json),
        json_dump(run.request_summary_json),
        json_dump(run.output_sections_json),
        json_dump(run.review_guidance_json),
        json_dump(run.guardrail_results_json),
        json_dump(run.lineage_json),
    )


def run_from_row(row: dict[str, Any]) -> AdvisoryCopilotRunRecord:
    return AdvisoryCopilotRunRecord(
        run_id=row["run_id"],
        schema_version=row["schema_version"],
        action_family=row["action_family"],
        audience=row["audience"],
        portfolio_id=row["portfolio_id"],
        proposal_id=row["proposal_id"],
        evidence_packet_id=row["evidence_packet_id"],
        evidence_packet_hash=row["evidence_packet_hash"],
        request_hash=row["request_hash"],
        output_hash=row["output_hash"],
        review_posture=row["review_posture"],
        client_ready_publication=row["client_ready_publication"],
        retention_class=row["retention_class"],
        legal_hold=bool(row["legal_hold"]),
        retention_expires_at=optional_datetime(row["retention_expires_at"]),
        created_by=row["created_by"],
        caller_app=row["caller_app"],
        tenant_id=row["tenant_id"],
        correlation_id=row["correlation_id"],
        idempotency_key=row["idempotency_key"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        lotus_ai_workflow_run_id=row["lotus_ai_workflow_run_id"],
        lotus_ai_model_version=row["lotus_ai_model_version"],
        workflow_pack_id=row["workflow_pack_id"],
        workflow_pack_version=row["workflow_pack_version"],
        prompt_template_version=row["prompt_template_version"],
        output_schema_version=row["output_schema_version"],
        evaluation_pack_ref=row["evaluation_pack_ref"],
        evidence_packet_json=json_load(row["evidence_packet_json"]),
        request_summary_json=json_load(row["request_summary_json"]),
        output_sections_json=json_load(row["output_sections_json"]),
        review_guidance_json=json_load(row["review_guidance_json"]),
        guardrail_results_json=json_load(row["guardrail_results_json"]),
        lineage_json=json_load(row["lineage_json"]),
    )


def evidence_packet_from_row(row: dict[str, Any]) -> AdvisoryCopilotEvidencePacketRecord:
    return AdvisoryCopilotEvidencePacketRecord(
        evidence_packet_id=row["evidence_packet_id"],
        evidence_packet_hash=row["evidence_packet_hash"],
        action_family=row["action_family"],
        audience=row["audience"],
        portfolio_id=row["portfolio_id"],
        proposal_id=row["proposal_id"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        correlation_id=row["correlation_id"],
        packet_json=json_load(row["packet_json"]),
        reason_json=json_load(row["reason_json"]),
    )


def review_from_row(row: dict[str, Any]) -> AdvisoryCopilotReviewRecord:
    return AdvisoryCopilotReviewRecord(
        review_id=row["review_id"],
        run_id=row["run_id"],
        schema_version=row["schema_version"],
        action=row["action"],
        previous_posture=row["previous_posture"],
        new_posture=row["new_posture"],
        actor_id=row["actor_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        reason_json=json_load(row["reason_json"]),
        request_hash=row["request_hash"],
        idempotency_key=row["idempotency_key"],
        correlation_id=row["correlation_id"],
    )


def json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def json_load(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def optional_datetime(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) and value else None


def can_refresh_source_projection_packet(
    *,
    existing: AdvisoryCopilotEvidencePacketRecord,
    incoming: AdvisoryCopilotEvidencePacketRecord,
) -> bool:
    same_projection = (
        existing.reason_json.get("source_projection") == "PROPOSAL_VERSION"
        and incoming.reason_json.get("source_projection") == "PROPOSAL_VERSION"
    )
    same_source = existing.reason_json.get("proposal_id") == incoming.reason_json.get(
        "proposal_id"
    ) and existing.reason_json.get("proposal_version_no") == incoming.reason_json.get(
        "proposal_version_no"
    )
    same_packet_identity = (
        existing.action_family == incoming.action_family
        and existing.audience == incoming.audience
        and existing.portfolio_id == incoming.portfolio_id
        and existing.proposal_id == incoming.proposal_id
    )
    return bool(same_projection and same_source and same_packet_identity)
