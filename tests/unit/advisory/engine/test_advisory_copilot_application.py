from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from src.core.advisory_copilot.api_limits import (
    COPILOT_REQUESTED_OUTPUT_LIMIT,
    COPILOT_REQUESTED_OUTPUT_MAX_LENGTH,
    COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT,
)
from src.core.advisory_copilot.api_models import (
    AdvisoryCopilotActionRequest,
    AdvisoryCopilotEvidencePacketCreateRequest,
    AdvisoryCopilotProposalVersionEvidenceRequest,
    AdvisoryCopilotReviewRequest,
)
from src.core.advisory_copilot.api_response_models import (
    AdvisoryCopilotSupportabilityResponse,
)
from src.core.advisory_copilot.api_validation import (
    normalize_bounded_copilot_string_tuple,
    normalize_copilot_actor_id,
    normalize_copilot_user_instruction,
    normalize_optional_copilot_identifier,
    normalize_required_copilot_identifier,
)
from src.core.advisory_copilot.application import AdvisoryCopilotApplicationService
from src.core.advisory_copilot.correlation import resolve_advisory_copilot_correlation_id
from src.core.advisory_copilot.proposal_projection_persistence import (
    save_proposal_version_advisory_copilot_evidence_packet,
)
from src.core.advisory_copilot.supportability import (
    build_advisory_copilot_supportability_response,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord, ProposalVersionRecord
from src.infrastructure.advisory_copilot import InMemoryAdvisoryCopilotRepository
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository
from src.integrations.lotus_ai import AdvisoryCopilotAiDraft

NOW = datetime(2026, 5, 28, 9, 0, tzinfo=UTC)


def test_copilot_action_request_normalizes_and_bounds_advisor_input() -> None:
    request = AdvisoryCopilotActionRequest(
        evidence_packet_id="copilot_packet_pb_sg_001",
        audience="ADVISOR",
        requested_outputs=[" advisor_review_summary ", "advisor_review_summary"],
        requested_by="  advisor_123  ",
        reason={"business_reason": "Prepare advisor review."},
        requested_intents=[" explain_policy_posture ", "explain_policy_posture"],
        user_instruction="  Summarize\n\n  advisor-use evidence.  ",
    )

    assert request.requested_outputs == ("advisor_review_summary",)
    assert request.requested_by == "advisor_123"
    assert request.requested_intents == ("explain_policy_posture",)
    assert request.user_instruction == "Summarize advisor-use evidence."

    with pytest.raises(ValidationError):
        AdvisoryCopilotActionRequest(
            evidence_packet_id="copilot_packet_pb_sg_001",
            audience="ADVISOR",
            requested_outputs=[],
            requested_by="advisor_123",
        )

    with pytest.raises(ValidationError):
        AdvisoryCopilotActionRequest(
            evidence_packet_id="copilot_packet_pb_sg_001",
            audience="ADVISOR",
            requested_outputs=["x" * 97],
            requested_by="advisor_123",
        )

    with pytest.raises(ValidationError):
        AdvisoryCopilotActionRequest(
            evidence_packet_id="copilot_packet_pb_sg_001",
            audience="ADVISOR",
            requested_outputs=["advisor_review_summary"],
            requested_by="advisor_123",
            user_instruction="x" * 1001,
        )


def test_copilot_api_validation_has_focused_owner() -> None:
    api_models_source = Path("src/core/advisory_copilot/api_models.py").read_text(encoding="utf-8")

    assert normalize_copilot_actor_id("  advisor_123  ") == "advisor_123"
    assert (
        normalize_required_copilot_identifier(
            "  copilot_packet_pb_sg_001  ",
            error_code="COPILOT_IDENTIFIER_REQUIRED",
        )
        == "copilot_packet_pb_sg_001"
    )
    assert normalize_optional_copilot_identifier(None) is None
    assert normalize_bounded_copilot_string_tuple(
        [" advisor_review_summary ", "advisor_review_summary", "risk_flags"],
        error_code="COPILOT_REQUESTED_OUTPUT_REQUIRED",
        max_items=8,
        max_item_length=96,
        allow_empty=False,
    ) == ("advisor_review_summary", "risk_flags")
    assert normalize_copilot_user_instruction("  Summarize\nadvisor evidence.  ") == (
        "Summarize advisor evidence."
    )
    with pytest.raises(ValueError, match="COPILOT_USER_INSTRUCTION_TOO_LONG"):
        normalize_copilot_user_instruction("x" * 1001)

    with pytest.raises(ValueError, match="COPILOT_IDENTIFIER_REQUIRED"):
        normalize_required_copilot_identifier(
            "   ",
            error_code="COPILOT_IDENTIFIER_REQUIRED",
        )
    with pytest.raises(ValueError, match="COPILOT_REQUESTED_OUTPUT_REQUIRED"):
        normalize_bounded_copilot_string_tuple(
            [],
            error_code="COPILOT_REQUESTED_OUTPUT_REQUIRED",
            max_items=8,
            max_item_length=96,
            allow_empty=False,
        )
    assert "def _normalize_copilot_actor_id(value: str)" not in api_models_source
    assert "def _normalize_required_identifier(value: str" not in api_models_source
    assert "def _normalize_bounded_string_tuple(" not in api_models_source
    assert "COPILOT_USER_INSTRUCTION_TOO_LONG" not in api_models_source


def test_copilot_api_limits_have_focused_owner() -> None:
    api_models_source = Path("src/core/advisory_copilot/api_models.py").read_text(encoding="utf-8")

    assert COPILOT_REQUESTED_OUTPUT_LIMIT == 8
    assert COPILOT_REQUESTED_OUTPUT_MAX_LENGTH == 96
    assert COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT == 12
    assert "_COPILOT_REQUESTED_OUTPUT_LIMIT" not in api_models_source
    assert "_COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT" not in api_models_source
    assert "COPILOT_REQUESTED_OUTPUT_LIMIT = 8" not in api_models_source


def test_copilot_api_response_models_have_focused_owner() -> None:
    api_models_source = Path("src/core/advisory_copilot/api_models.py").read_text(encoding="utf-8")
    response_models_source = Path("src/core/advisory_copilot/api_response_models.py").read_text(
        encoding="utf-8"
    )

    assert AdvisoryCopilotSupportabilityResponse.__module__.endswith("api_response_models")
    assert "class AdvisoryCopilotSupportabilityResponse" not in api_models_source
    assert "class AdvisoryCopilotRunResponse" not in api_models_source
    assert "class AdvisoryCopilotRunPage" not in api_models_source
    assert "class AdvisoryCopilotSupportabilityResponse" in response_models_source


def test_copilot_evidence_packet_requests_normalize_and_bound_identifiers() -> None:
    create_request = AdvisoryCopilotEvidencePacketCreateRequest(
        evidence_packet_id="  copilot_packet_pb_sg_001  ",
        action_family="PROPOSAL_EXPLANATION",
        portfolio_id="  PB_SG_GLOBAL_BAL_001  ",
        proposal_id="  proposal_sg_structured_note_001  ",
        audience="ADVISOR",
        source_sections=(),
        created_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
    )
    projection_request = AdvisoryCopilotProposalVersionEvidenceRequest(
        proposal_id="  proposal_sg_structured_note_001  ",
        proposal_version_no=1,
        evidence_packet_id="  copilot_packet_pb_sg_001  ",
        action_family="PROPOSAL_EXPLANATION",
        audience="ADVISOR",
        created_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
    )

    assert create_request.evidence_packet_id == "copilot_packet_pb_sg_001"
    assert create_request.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert create_request.proposal_id == "proposal_sg_structured_note_001"
    assert projection_request.proposal_id == "proposal_sg_structured_note_001"
    assert projection_request.evidence_packet_id == "copilot_packet_pb_sg_001"

    with pytest.raises(ValidationError):
        AdvisoryCopilotEvidencePacketCreateRequest(
            evidence_packet_id="x" * 161,
            action_family="PROPOSAL_EXPLANATION",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            audience="ADVISOR",
            source_sections=(),
            created_by="advisor_123",
        )

    with pytest.raises(ValidationError):
        AdvisoryCopilotProposalVersionEvidenceRequest(
            proposal_id=" ",
            proposal_version_no=1,
            action_family="PROPOSAL_EXPLANATION",
            audience="ADVISOR",
            created_by="advisor_123",
        )


def test_copilot_review_request_bounds_actor_id() -> None:
    request = AdvisoryCopilotReviewRequest(
        action="APPROVE_FOR_INTERNAL_USE",
        actor_id="  supervisor_123  ",
        reason={"decision": "Reviewed against cited source evidence."},
    )

    assert request.actor_id == "supervisor_123"

    with pytest.raises(ValidationError):
        AdvisoryCopilotReviewRequest(
            action="APPROVE_FOR_INTERNAL_USE",
            actor_id="x" * 129,
            reason={"decision": "Reviewed against cited source evidence."},
        )


def test_copilot_correlation_resolution_uses_shared_validation_and_stable_fallback() -> None:
    assert (
        resolve_advisory_copilot_correlation_id(
            "  corr-advisor-request-001  ",
            fallback="corr-fallback",
        )
        == "corr-advisor-request-001"
    )
    assert (
        resolve_advisory_copilot_correlation_id(
            None,
            fallback="corr-copilot_packet_pb_sg_001",
        )
        == "corr-copilot_packet_pb_sg_001"
    )

    resolved = resolve_advisory_copilot_correlation_id(
        None,
        fallback="x" * 129,
    )

    assert resolved.startswith("corr-")
    assert len(resolved) == 29


def test_copilot_supportability_response_has_focused_owner() -> None:
    application_source = Path("src/core/advisory_copilot/application.py").read_text(
        encoding="utf-8"
    )
    route_source = Path("src/api/proposals/routes_advisory_copilot.py").read_text(encoding="utf-8")

    response = build_advisory_copilot_supportability_response()

    assert response.support_status == "ADVISE_COPILOT_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"
    assert response.client_ready_publication == "BLOCKED"
    assert response.supported_action_families
    assert "CLIENT_READY_PUBLICATION is blocked" in response.boundaries
    assert "def build_advisory_copilot_supportability_response" not in application_source
    assert "from src.core.advisory_copilot.supportability import" in route_source


def _seed_proposal_version(repository: InMemoryProposalRepository) -> None:
    repository.create_proposal(
        ProposalRecord(
            proposal_id="proposal_sg_structured_note_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            created_by="advisor_123",
            created_at=NOW,
            last_event_at=NOW,
            current_state="COMPLIANCE_REVIEW",
            current_version_no=1,
            title="Structured note proposal review",
        )
    )
    repository.create_version(
        ProposalVersionRecord(
            proposal_version_id="version_sg_001",
            proposal_id="proposal_sg_structured_note_001",
            version_no=1,
            created_at=NOW,
            request_hash="sha256:request",
            artifact_hash="sha256:artifact",
            simulation_hash="sha256:simulation",
            status_at_creation="READY",
            proposal_result_json={"status": "READY"},
            artifact_json={"narrative": {"status": "REVIEW_REQUIRED"}},
            evidence_bundle_json={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        )
    )
    repository.create_memo(
        ProposalMemoRecord(
            memo_id="memo_sg_001",
            proposal_id="proposal_sg_structured_note_001",
            proposal_version_no=1,
            proposal_version_id="version_sg_001",
            artifact_id="artifact_sg_001",
            memo_version="advisory-proposal-memo-evidence-pack.v1",
            memo_status="BLOCKED",
            lifecycle_status="FINALIZED",
            created_by="advisor_123",
            created_at=NOW,
            source_input_hash="sha256:memo-source",
            memo_hash="sha256:memo",
            memo_json={"memo_id": "memo_sg_001"},
            report_package_events_json=[
                {"event_id": "memo_report_pkg_001", "report_reference_id": "report_pkg_001"}
            ],
        )
    )


def _policy_evaluation() -> PolicyEvaluationRecord:
    return PolicyEvaluationRecord(
        evaluation_id="policy_eval_sg_001",
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id="version_sg_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        generated_at="2026-05-28T09:00:00+00:00",
        created_by="advisor_123",
        evaluation_status="PENDING_REVIEW",
        policy_content_hash="sha256:policy-content",
        source_evidence_hash="sha256:source-evidence",
        evaluation_hash="sha256:policy-evaluation",
        evaluation_json={"evaluation_status": "PENDING_REVIEW"},
        approval_dependencies=["COMPLIANCE_REVIEW"],
    )


def _evidence_packet_request() -> AdvisoryCopilotEvidencePacketCreateRequest:
    return AdvisoryCopilotEvidencePacketCreateRequest(
        evidence_packet_id="copilot_packet_pb_sg_001",
        action_family="PROPOSAL_EXPLANATION",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proposal_id="proposal_sg_structured_note_001",
        audience="ADVISOR",
        created_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
        source_sections=(
            {
                "section_key": "POLICY_POSTURE",
                "title": "Policy posture",
                "evidence_class": "COMPLIANCE_REVIEW_EVIDENCE",
                "source_refs": (
                    {
                        "source_system": "lotus-advise",
                        "source_type": "POLICY_EVALUATION",
                        "source_id": "policy_eval_sg_001",
                        "content_hash": "sha256:policy-evaluation",
                        "access_class": "COMPLIANCE_REVIEW_EVIDENCE",
                    },
                ),
                "summary_items": ("Policy evaluation requires compliance review.",),
                "allowed_audiences": ("ADVISOR", "COMPLIANCE_REVIEWER"),
            },
        ),
    )


def _draft_generator(**kwargs: Any) -> AdvisoryCopilotAiDraft:
    lineage = {
        "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
        "workflow_pack_version": "v1",
        "workflow_run_id": "packrun_copilot_001",
        "model_version": "lotus-ai-governed-model.v1",
        "proposal_version_id": "version_sg_001",
    }
    return AdvisoryCopilotAiDraft(
        status="REVIEW_REQUIRED",
        sections=(
            {
                "section_key": "SUMMARY",
                "title": "Advisor summary",
                "text": "Policy review is required before client communication.",
            },
        ),
        lineage=lineage,
        review_guidance=("Review source evidence before internal use.",),
        guardrail_reasons=(),
    )


def test_application_service_projects_proposal_version_with_injected_policy_loader() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    proposal_repository = InMemoryProposalRepository()
    _seed_proposal_version(proposal_repository)
    loader_calls: list[dict[str, str | None]] = []

    def _load_policy_evaluations(**kwargs: str | None) -> list[PolicyEvaluationRecord]:
        loader_calls.append(dict(kwargs))
        return [_policy_evaluation()]

    service = AdvisoryCopilotApplicationService(
        repository=copilot_repository,
        draft_generator=_draft_generator,
        policy_evaluation_loader=_load_policy_evaluations,
    )

    response = service.create_proposal_version_evidence_packet(
        payload=AdvisoryCopilotProposalVersionEvidenceRequest(
            proposal_id="proposal_sg_structured_note_001",
            proposal_version_no=1,
            action_family="PROPOSAL_EXPLANATION",
            audience="ADVISOR",
            created_by="  advisor_123  ",
            reason={"business_reason": "Prepare advisor copilot review."},
        ),
        proposal_repository=proposal_repository,
        correlation_id="  corr_projection_001  ",
    )

    assert loader_calls == [{"evaluation_status": None, "portfolio_id": "PB_SG_GLOBAL_BAL_001"}]
    assert response.evidence_packet.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert response.evidence_packet.client_ready_publication == "BLOCKED"
    assert {section.section_key for section in response.evidence_packet.sections} >= {
        "PROPOSAL_CONTEXT",
        "NARRATIVE_POSTURE",
        "MEMO_EVIDENCE",
        "POLICY_POSTURE",
    }
    assert response.record.reason_json["source_projection"] == "PROPOSAL_VERSION"
    assert response.record.correlation_id == "corr_projection_001"
    assert response.record.created_by == "advisor_123"


def test_copilot_proposal_projection_persistence_has_focused_owner() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    proposal_repository = InMemoryProposalRepository()
    _seed_proposal_version(proposal_repository)
    application_source = Path("src/core/advisory_copilot/application.py").read_text(
        encoding="utf-8"
    )

    response = save_proposal_version_advisory_copilot_evidence_packet(
        repository=copilot_repository,
        proposal_repository=proposal_repository,
        payload=AdvisoryCopilotProposalVersionEvidenceRequest(
            proposal_id="proposal_sg_structured_note_001",
            proposal_version_no=1,
            action_family="PROPOSAL_EXPLANATION",
            audience="ADVISOR",
            created_by="advisor_123",
            reason={"business_reason": "Prepare advisor copilot review."},
        ),
        policy_evaluations=(_policy_evaluation(),),
        correlation_id="corr_projection_owner_001",
    )

    assert response.record.reason_json["source_projection"] == "PROPOSAL_VERSION"
    assert response.record.correlation_id == "corr_projection_owner_001"
    assert response.evidence_packet.proposal_id == "proposal_sg_structured_note_001"
    assert "build_proposal_version_copilot_evidence_packet" not in application_source
    assert '"source_projection": "PROPOSAL_VERSION"' not in application_source


def test_application_service_bounds_source_projection_evidence_text() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    proposal_repository = InMemoryProposalRepository()
    proposal_id = f"proposal_{'sg_' * 40}"
    proposal_version_id = f"version_{'oversized_' * 24}"
    memo_id = f"memo_{'archive_reference_' * 12}"
    oversized_text = "source evidence item " * 160
    proposal_repository.create_proposal(
        ProposalRecord(
            proposal_id=proposal_id,
            portfolio_id=f"PB_SG_GLOBAL_BAL_{'001_' * 30}",
            created_by="advisor_123",
            created_at=NOW,
            last_event_at=NOW,
            current_state="COMPLIANCE_REVIEW",
            current_version_no=1,
            title=oversized_text,
        )
    )
    proposal_repository.create_version(
        ProposalVersionRecord(
            proposal_version_id=proposal_version_id,
            proposal_id=proposal_id,
            version_no=1,
            created_at=NOW,
            request_hash="sha256:request",
            artifact_hash=f"sha256:{'artifact' * 40}",
            simulation_hash="sha256:simulation",
            status_at_creation="READY",
            proposal_result_json={"status": "READY"},
            artifact_json={"narrative": {"status": oversized_text}},
            evidence_bundle_json={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        )
    )
    proposal_repository.create_memo(
        ProposalMemoRecord(
            memo_id=memo_id,
            proposal_id=proposal_id,
            proposal_version_no=1,
            proposal_version_id=proposal_version_id,
            artifact_id="artifact_sg_001",
            memo_version="advisory-proposal-memo-evidence-pack.v1",
            memo_status="BLOCKED",
            lifecycle_status="FINALIZED",
            created_by="advisor_123",
            created_at=NOW,
            source_input_hash="sha256:memo-source",
            memo_hash=f"sha256:{'memo' * 40}",
            memo_json={"memo_id": memo_id},
            report_package_events_json=[
                {
                    "event_id": f"memo_report_pkg_{'001_' * 50}",
                    "report_reference_id": f"report_pkg_{'001_' * 50}",
                }
            ],
            archive_refs_json=[{"archive_ref": f"archive_ref_{'001_' * 360}"}],
        )
    )

    def _load_policy_evaluations(**_: str | None) -> list[PolicyEvaluationRecord]:
        return [
            PolicyEvaluationRecord(
                evaluation_id=f"policy_eval_{'sg_' * 60}",
                proposal_id=proposal_id,
                proposal_version_id=proposal_version_id,
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                policy_pack_id=f"SG_PRIVATE_BANKING_REFERENCE_{'A' * 200}",
                policy_version=f"2026.05.{'1' * 200}",
                generated_at="2026-05-28T09:00:00+00:00",
                created_by="advisor_123",
                evaluation_status="PENDING_REVIEW",
                policy_content_hash="sha256:policy-content",
                source_evidence_hash="sha256:source-evidence",
                evaluation_hash=f"sha256:{'policy-evaluation' * 20}",
                evaluation_json={"evaluation_status": "PENDING_REVIEW"},
                approval_dependencies=[oversized_text],
                disclosure_requirements=[oversized_text],
                consent_requirements=[oversized_text],
                source_gaps=[oversized_text],
            )
        ]

    service = AdvisoryCopilotApplicationService(
        repository=copilot_repository,
        draft_generator=_draft_generator,
        policy_evaluation_loader=_load_policy_evaluations,
    )

    response = service.create_proposal_version_evidence_packet(
        payload=AdvisoryCopilotProposalVersionEvidenceRequest(
            proposal_id=proposal_id,
            proposal_version_no=1,
            action_family="PROPOSAL_EXPLANATION",
            audience="ADVISOR",
            created_by="advisor_123",
            reason={"business_reason": "Prepare advisor copilot review."},
        ),
        proposal_repository=proposal_repository,
        correlation_id="corr_projection_bounds_001",
    )

    packet = response.evidence_packet
    assert len(packet.evidence_packet_id) <= 160
    for lineage_ref in packet.lineage_refs:
        assert len(lineage_ref.lineage_id) <= 160
    for section in packet.sections:
        for source_ref in section.source_refs:
            assert len(source_ref.source_id) <= 160
            if source_ref.content_hash is not None:
                assert len(source_ref.content_hash) <= 128
        for summary in section.summary_items:
            assert len(summary) <= 1000


def test_application_service_run_action_keeps_raw_instruction_out_of_persistence() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    draft_calls: list[dict[str, Any]] = []

    def _capturing_draft_generator(**kwargs: Any) -> AdvisoryCopilotAiDraft:
        draft_calls.append(dict(kwargs))
        return _draft_generator(**kwargs)

    service = AdvisoryCopilotApplicationService(
        repository=copilot_repository,
        draft_generator=_capturing_draft_generator,
        policy_evaluation_loader=lambda **_: (),
    )
    service.create_evidence_packet(
        payload=_evidence_packet_request(),
        correlation_id="corr_packet_001",
    )

    first = service.run_action(
        payload=AdvisoryCopilotActionRequest(
            evidence_packet_id="copilot_packet_pb_sg_001",
            audience="ADVISOR",
            requested_outputs=("advisor_review_summary",),
            requested_by="  advisor_123  ",
            reason={"business_reason": "Prepare advisor review."},
            requested_intents=("explain_policy_posture",),
            user_instruction="Summarize the advisory evidence for internal review.",
        ),
        idempotency_key="  copilot-action-idem-001  ",
        correlation_id="  corr_action_001  ",
    )
    replay = service.run_action(
        payload=AdvisoryCopilotActionRequest(
            evidence_packet_id="copilot_packet_pb_sg_001",
            audience="ADVISOR",
            requested_outputs=("advisor_review_summary",),
            requested_by="advisor_123",
            reason={"business_reason": "Prepare advisor review."},
            requested_intents=("explain_policy_posture",),
            user_instruction="Summarize the advisory evidence for internal review.",
        ),
        idempotency_key="copilot-action-idem-001",
        correlation_id=None,
    )
    with pytest.raises(ValueError, match="COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT"):
        service.run_action(
            payload=AdvisoryCopilotActionRequest(
                evidence_packet_id="copilot_packet_pb_sg_001",
                audience="ADVISOR",
                requested_outputs=("advisor_review_summary",),
                requested_by="advisor_123",
                reason={"business_reason": "Different advisor review."},
                requested_intents=("explain_policy_posture",),
                user_instruction="Summarize the advisory evidence for internal review.",
            ),
            idempotency_key="copilot-action-idem-001",
            correlation_id=None,
        )

    assert draft_calls[0]["requested_intents"] == ("explain_policy_posture",)
    assert draft_calls[0]["user_instruction"] == (
        "Summarize the advisory evidence for internal review."
    )
    assert first.replayed is False
    assert replay.replayed is True
    assert len(draft_calls) == 1
    assert first.run.run_id == replay.run.run_id
    assert first.run.idempotency_key == "copilot-action-idem-001"
    assert first.run.created_by == "advisor_123"
    assert first.run.correlation_id == "corr_action_001"
    assert first.run.request_summary_json["user_instruction_hash"].startswith("sha256:")
    assert "user_instruction" not in first.run.request_summary_json
    assert "Summarize the advisory evidence" not in str(first.run.model_dump(mode="json"))


def test_application_service_uses_deterministic_correlation_fallback_for_blank_values() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    service = AdvisoryCopilotApplicationService(
        repository=copilot_repository,
        draft_generator=_draft_generator,
        policy_evaluation_loader=lambda **_: (),
    )
    packet = service.create_evidence_packet(
        payload=_evidence_packet_request(),
        correlation_id="   ",
    )
    run = service.run_action(
        payload=AdvisoryCopilotActionRequest(
            evidence_packet_id="copilot_packet_pb_sg_001",
            audience="ADVISOR",
            requested_outputs=("advisor_review_summary",),
            requested_by="advisor_123",
            reason={"business_reason": "Prepare advisor review."},
        ),
        idempotency_key=None,
        correlation_id="   ",
    )

    assert packet.record.correlation_id == "corr-copilot_packet_pb_sg_001"
    assert run.run.correlation_id == "corr-copilot_packet_pb_sg_001"


def test_application_service_bounds_generated_correlation_fallback() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    service = AdvisoryCopilotApplicationService(
        repository=copilot_repository,
        draft_generator=_draft_generator,
        policy_evaluation_loader=lambda **_: (),
    )
    packet_id = f"copilot_packet_{'x' * 145}"

    response = service.create_evidence_packet(
        payload=AdvisoryCopilotEvidencePacketCreateRequest(
            evidence_packet_id=packet_id,
            action_family="PROPOSAL_EXPLANATION",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            proposal_id="proposal_sg_structured_note_001",
            audience="ADVISOR",
            source_sections=(),
            created_by="advisor_123",
            reason={"business_reason": "Prepare advisor review."},
        ),
        correlation_id="   ",
    )

    assert response.record.correlation_id.startswith("corr-")
    assert len(response.record.correlation_id) <= 128


def test_application_service_rejects_invalid_copilot_run_page_size() -> None:
    service = AdvisoryCopilotApplicationService(
        repository=InMemoryAdvisoryCopilotRepository(),
        draft_generator=_draft_generator,
        policy_evaluation_loader=lambda **_: (),
    )

    with pytest.raises(ValueError, match="COPILOT_RUN_PAGE_SIZE_INVALID"):
        service.list_proposal_version_runs(
            proposal_id="proposal_sg_structured_note_001",
            version_id="version_sg_001",
            limit=0,
            cursor=None,
        )


def test_application_service_refreshes_retryable_unavailable_copilot_run() -> None:
    copilot_repository = InMemoryAdvisoryCopilotRepository()
    draft_calls: list[dict[str, Any]] = []
    drafts = iter(
        [
            AdvisoryCopilotAiDraft(
                status="UNAVAILABLE",
                sections=(),
                lineage={
                    "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
                    "workflow_pack_version": "v1",
                    "workflow_run_id": None,
                    "model_version": None,
                    "proposal_version_id": "version_sg_001",
                    "fallback_reason": "LOTUS_AI_ADVISORY_COPILOT_UNAVAILABLE",
                },
                review_guidance=("Retry after lotus-ai availability is restored.",),
                guardrail_reasons=(),
            ),
            _draft_generator(),
        ]
    )

    def _sequenced_draft_generator(**kwargs: Any) -> AdvisoryCopilotAiDraft:
        draft_calls.append(dict(kwargs))
        return next(drafts)

    service = AdvisoryCopilotApplicationService(
        repository=copilot_repository,
        draft_generator=_sequenced_draft_generator,
        policy_evaluation_loader=lambda **_: (),
    )
    service.create_evidence_packet(
        payload=_evidence_packet_request(),
        correlation_id="corr_packet_001",
    )
    request = AdvisoryCopilotActionRequest(
        evidence_packet_id="copilot_packet_pb_sg_001",
        audience="ADVISOR",
        requested_outputs=("advisor_review_summary",),
        requested_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
        requested_intents=("explain_policy_posture",),
        user_instruction="Summarize the advisory evidence for internal review.",
    )

    unavailable = service.run_action(
        payload=request,
        idempotency_key="copilot-action-idem-refresh",
        correlation_id="corr_action_001",
    )
    refreshed = service.run_action(
        payload=request,
        idempotency_key="copilot-action-idem-refresh",
        correlation_id="corr_action_002",
    )
    replay = service.run_action(
        payload=request,
        idempotency_key="copilot-action-idem-refresh",
        correlation_id="corr_action_003",
    )

    assert unavailable.run.review_posture == "UNAVAILABLE"
    assert refreshed.replayed is False
    assert refreshed.run.run_id == unavailable.run.run_id
    assert refreshed.run.created_at == unavailable.run.created_at
    assert refreshed.run.review_posture == "REVIEW_REQUIRED"
    assert refreshed.run.output_sections_json[0]["section_key"] == "SUMMARY"
    assert replay.replayed is True
    assert replay.run.review_posture == "REVIEW_REQUIRED"
    assert len(draft_calls) == 2
