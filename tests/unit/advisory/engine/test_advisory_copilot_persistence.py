from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.advisory_copilot import (
    CopilotEvidencePacket,
    CopilotEvidencePacketSection,
    CopilotLineageRef,
    CopilotSourceRef,
    list_advisory_copilot_reviews,
    persist_advisory_copilot_run,
    record_advisory_copilot_review,
)
from src.infrastructure.advisory_copilot import InMemoryAdvisoryCopilotRepository


def _packet() -> CopilotEvidencePacket:
    source_ref = CopilotSourceRef(
        source_system="lotus-advise",
        source_type="POLICY_EVALUATION",
        source_id="policy_eval_sg_001",
        content_hash="sha256:policy-evaluation",
        access_class="COMPLIANCE_REVIEW_EVIDENCE",
    )
    return CopilotEvidencePacket(
        evidence_packet_id="copilot_packet_pb_sg_001",
        evidence_packet_hash="sha256:copilot-evidence-packet-001",
        action_family="PROPOSAL_EXPLANATION",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proposal_id="proposal_sg_structured_note_001",
        sections=(
            CopilotEvidencePacketSection(
                section_key="POLICY_POSTURE",
                title="Policy posture",
                evidence_class="COMPLIANCE_REVIEW_EVIDENCE",
                source_refs=(source_ref,),
                summary_items=("Policy evaluation requires compliance review.",),
            ),
        ),
        lineage_refs=(
            CopilotLineageRef(
                lineage_type="EVIDENCE_PACKET",
                lineage_id="copilot_packet_pb_sg_001",
                source_system="lotus-advise",
            ),
        ),
        retention_class="ADVISORY_REVIEW_RECORD",
    )


def _persist_run(
    repository: InMemoryAdvisoryCopilotRepository,
    *,
    draft_status: str = "REVIEW_REQUIRED",
    output_sections: tuple[dict[str, str], ...] | None = None,
    lineage: dict[str, str | int | None] | None = None,
):
    if output_sections is None:
        output_sections = (
            {
                "section_key": "SUMMARY",
                "title": "Advisor summary",
                "text": "Policy review is required before client communication.",
            },
        )
    if lineage is None:
        lineage = {
            "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
            "workflow_pack_version": "v1",
            "workflow_run_id": "packrun_copilot_001",
            "model_version": "stub-advisory-copilot-v1",
            "prompt_template_version": "advisory-copilot-prompt-template.v1",
            "output_schema_version": "advisory-copilot-output-schema.v1",
            "evaluation_pack_ref": "advisory-copilot-eval-pack.v1",
            "proposal_version_no": 1,
        }
    return persist_advisory_copilot_run(
        repository=repository,
        evidence_packet=_packet(),
        audience="ADVISOR",
        requested_outputs=("advisor_review_summary",),
        requested_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
        draft_status=draft_status,
        output_sections=output_sections,
        lineage=lineage,
        review_guidance=("Review source evidence before internal use.",),
        guardrail_reasons=(),
        correlation_id="corr_rfc0027_copilot_001",
        idempotency_key="copilot-action-idem-001",
        requested_intents=("explain_policy_posture",),
        user_instruction="Summarize the advisory evidence for internal review.",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
    )


def test_persisted_copilot_run_is_replayable_and_excludes_raw_prompt() -> None:
    repository = InMemoryAdvisoryCopilotRepository()

    result = _persist_run(repository)
    replay = _persist_run(repository)

    assert result.replayed is False
    assert replay.replayed is True
    assert replay.run.run_id == result.run.run_id
    assert result.run.review_posture == "REVIEW_REQUIRED"
    assert result.run.client_ready_publication == "BLOCKED"
    assert result.run.lotus_ai_workflow_run_id == "packrun_copilot_001"
    assert result.run.retention_expires_at is not None
    assert result.run.retention_expires_at.year == 2033
    assert result.run.evidence_packet_json["evidence_packet_id"] == "copilot_packet_pb_sg_001"
    assert "user_instruction_hash" in result.run.request_summary_json
    assert "Summarize the advisory evidence" not in str(result.run.model_dump(mode="json"))

    runs = repository.list_runs_for_proposal_version(
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id=None,
        proposal_version_no=1,
    )
    assert [run.run_id for run in runs] == [result.run.run_id]


def test_retrying_dependency_unavailable_copilot_run_refreshes_same_idempotent_request() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    unavailable = _persist_run(
        repository,
        draft_status="UNAVAILABLE",
        output_sections=(),
        lineage={
            "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
            "workflow_pack_version": "v1",
            "workflow_run_id": None,
            "model_version": None,
            "prompt_template_version": "advisory-copilot-prompt-template.v1",
            "output_schema_version": "advisory-copilot-output-schema.v1",
            "evaluation_pack_ref": "advisory-copilot-eval-pack.v1",
            "proposal_version_no": 1,
            "fallback_reason": "LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
        },
    )
    refreshed = _persist_run(repository)

    assert unavailable.run.review_posture == "UNAVAILABLE"
    assert refreshed.replayed is False
    assert refreshed.run.run_id == unavailable.run.run_id
    assert refreshed.run.created_at == unavailable.run.created_at
    assert refreshed.run.review_posture == "REVIEW_REQUIRED"
    assert refreshed.run.lotus_ai_workflow_run_id == "packrun_copilot_001"
    assert refreshed.run.output_sections_json[0]["section_key"] == "SUMMARY"


def test_retrying_false_positive_output_guardrail_refreshes_same_idempotent_request() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    first = persist_advisory_copilot_run(
        repository=repository,
        evidence_packet=_packet(),
        audience="ADVISOR",
        requested_outputs=("advisor_review_summary",),
        requested_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
        draft_status="GUARDRAIL_REJECTED",
        output_sections=(),
        lineage={
            "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
            "workflow_pack_version": "v1",
            "workflow_run_id": "packrun_false_positive",
            "model_version": "stub-advisory-copilot-v1",
            "prompt_template_version": "advisory-copilot-prompt-template.v1",
            "output_schema_version": "advisory-copilot-output-schema.v1",
            "evaluation_pack_ref": "advisory-copilot-eval-pack.v1",
            "proposal_version_no": 1,
            "fallback_reason": "COPILOT_OUTPUT_GUARDRAIL_REJECTED",
        },
        review_guidance=("The advisory copilot request was blocked.",),
        guardrail_reasons=("CLIENT_READY_PUBLICATION_FORBIDDEN",),
        correlation_id="corr_rfc0027_copilot_001",
        idempotency_key="copilot-action-idem-001",
        requested_intents=("explain_policy_posture",),
        user_instruction="Summarize the advisory evidence for internal review.",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
    )
    refreshed = _persist_run(
        repository,
        output_sections=(
            {
                "section_key": "NARRATIVE_POSTURE",
                "title": "Narrative posture",
                "text": "Client-ready publication remains blocked until review gates pass.",
            },
        ),
    )

    assert first.run.review_posture == "GUARDRAIL_REJECTED"
    assert refreshed.replayed is False
    assert refreshed.run.run_id == first.run.run_id
    assert refreshed.run.created_at == first.run.created_at
    assert refreshed.run.review_posture == "REVIEW_REQUIRED"
    assert refreshed.run.guardrail_results_json == []
    assert refreshed.run.output_sections_json[0]["section_key"] == "NARRATIVE_POSTURE"


def test_copilot_run_idempotency_rejects_changed_request() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    _persist_run(repository)

    with pytest.raises(ValueError, match="COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT"):
        persist_advisory_copilot_run(
            repository=repository,
            evidence_packet=_packet(),
            audience="ADVISOR",
            requested_outputs=("different_output",),
            requested_by="advisor_123",
            reason={"business_reason": "Prepare advisor review."},
            draft_status="REVIEW_REQUIRED",
            output_sections=(),
            lineage={"workflow_pack_id": "advisory_copilot_proposal_explanation.pack"},
            review_guidance=(),
            guardrail_reasons=(),
            correlation_id="corr_rfc0027_copilot_001",
            idempotency_key="copilot-action-idem-001",
        )


def test_copilot_review_actions_are_idempotent_and_audited() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    run = _persist_run(repository).run

    review = record_advisory_copilot_review(
        repository=repository,
        run_id=run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        actor_id="supervisor_123",
        reason={"decision": "Reviewed against cited source evidence."},
        correlation_id="corr_rfc0027_review_001",
        idempotency_key="copilot-review-idem-001",
        occurred_at=datetime(2026, 5, 28, 9, 5, tzinfo=timezone.utc),
    )
    replay = record_advisory_copilot_review(
        repository=repository,
        run_id=run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        actor_id="supervisor_123",
        reason={"decision": "Reviewed against cited source evidence."},
        correlation_id="corr_rfc0027_review_001",
        idempotency_key="copilot-review-idem-001",
        occurred_at=datetime(2026, 5, 28, 9, 6, tzinfo=timezone.utc),
    )

    assert review.replayed is False
    assert replay.replayed is True
    assert review.run.review_posture == "APPROVED_FOR_INTERNAL_USE"
    assert replay.review.review_id == review.review.review_id
    assert list_advisory_copilot_reviews(repository=repository, run_id=run.run_id) == (
        review.review,
    )

    with pytest.raises(ValueError, match="COPILOT_RUN_REVIEW_POSTURE_TERMINAL"):
        record_advisory_copilot_review(
            repository=repository,
            run_id=run.run_id,
            action="REJECT",
            actor_id="supervisor_123",
            reason={"decision": "Changed mind."},
            correlation_id="corr_rfc0027_review_002",
        )


def test_copilot_persistence_rejects_raw_ai_payloads() -> None:
    repository = InMemoryAdvisoryCopilotRepository()

    with pytest.raises(ValueError, match="COPILOT_RAW_AI_PAYLOAD_NOT_ALLOWED"):
        persist_advisory_copilot_run(
            repository=repository,
            evidence_packet=_packet(),
            audience="ADVISOR",
            requested_outputs=("advisor_review_summary",),
            requested_by="advisor_123",
            reason={"raw_prompt": "write something client-ready"},
            draft_status="REVIEW_REQUIRED",
            output_sections=(),
            lineage={"workflow_pack_id": "advisory_copilot_proposal_explanation.pack"},
            review_guidance=(),
            guardrail_reasons=(),
            correlation_id="corr_rfc0027_copilot_001",
        )
