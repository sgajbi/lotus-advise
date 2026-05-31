from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from src.core.advisory_copilot import (
    AdvisoryCopilotEvidencePacketRecord,
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunIdempotencyRecord,
    AdvisoryCopilotRunRecord,
    CopilotEvidencePacket,
    CopilotEvidencePacketSection,
    CopilotLineageRef,
    CopilotSourceRef,
    list_advisory_copilot_reviews,
    load_advisory_copilot_evidence_packet,
    persist_advisory_copilot_run,
    record_advisory_copilot_review,
    save_advisory_copilot_evidence_packet,
)
from src.infrastructure.advisory_copilot import InMemoryAdvisoryCopilotRepository
from src.infrastructure.advisory_copilot.postgres import PostgresAdvisoryCopilotRepository

_RUN_COLUMNS = (
    "run_id",
    "schema_version",
    "action_family",
    "audience",
    "portfolio_id",
    "proposal_id",
    "evidence_packet_id",
    "evidence_packet_hash",
    "request_hash",
    "output_hash",
    "review_posture",
    "client_ready_publication",
    "retention_class",
    "legal_hold",
    "retention_expires_at",
    "created_by",
    "caller_app",
    "tenant_id",
    "correlation_id",
    "idempotency_key",
    "created_at",
    "updated_at",
    "lotus_ai_workflow_run_id",
    "lotus_ai_model_version",
    "workflow_pack_id",
    "workflow_pack_version",
    "prompt_template_version",
    "output_schema_version",
    "evaluation_pack_ref",
    "evidence_packet_json",
    "request_summary_json",
    "output_sections_json",
    "review_guidance_json",
    "guardrail_results_json",
    "lineage_json",
)


_EVIDENCE_PACKET_COLUMNS = (
    "evidence_packet_id",
    "evidence_packet_hash",
    "action_family",
    "audience",
    "portfolio_id",
    "proposal_id",
    "created_by",
    "created_at",
    "correlation_id",
    "packet_json",
    "reason_json",
)


_REVIEW_COLUMNS = (
    "review_id",
    "run_id",
    "schema_version",
    "action",
    "previous_posture",
    "new_posture",
    "actor_id",
    "occurred_at",
    "reason_json",
    "request_hash",
    "idempotency_key",
    "correlation_id",
)


class _FakePostgresConnection:
    def __init__(self) -> None:
        self.evidence_packets: dict[str, dict[str, Any]] = {}
        self.runs: dict[str, dict[str, Any]] = {}
        self.run_idempotency: dict[str, dict[str, Any]] = {}
        self.reviews: dict[str, dict[str, Any]] = {}
        self.commits = 0
        self._one: dict[str, Any] | None = None
        self._all: list[dict[str, Any]] = []

    def execute(
        self, query: str, params: tuple[Any, ...] | list[Any] = ()
    ) -> "_FakePostgresConnection":
        sql = " ".join(query.split())
        args = tuple(params)
        self._one = None
        self._all = []

        if sql.startswith("SELECT * FROM advisory_copilot_evidence_packets"):
            self._one = self.evidence_packets.get(str(args[0]))
            return self
        if sql.startswith("INSERT INTO advisory_copilot_evidence_packets"):
            row = dict(zip(_EVIDENCE_PACKET_COLUMNS, args, strict=True))
            self.evidence_packets.setdefault(str(row["evidence_packet_id"]), row)
            return self
        if sql.startswith("UPDATE advisory_copilot_evidence_packets"):
            evidence_packet_id = str(args[-1])
            existing = self.evidence_packets[evidence_packet_id]
            existing.update(
                {
                    "evidence_packet_hash": args[0],
                    "action_family": args[1],
                    "audience": args[2],
                    "portfolio_id": args[3],
                    "proposal_id": args[4],
                    "created_by": args[5],
                    "created_at": args[6],
                    "correlation_id": args[7],
                    "packet_json": args[8],
                    "reason_json": args[9],
                }
            )
            return self

        if sql.startswith("SELECT idempotency_key"):
            self._one = self.run_idempotency.get(str(args[0]))
            return self
        if sql.startswith("SELECT * FROM advisory_copilot_runs WHERE run_id"):
            self._one = self.runs.get(str(args[0]))
            return self
        if sql.startswith("INSERT INTO advisory_copilot_runs"):
            row = dict(zip(_RUN_COLUMNS, args, strict=True))
            self.runs.setdefault(str(row["run_id"]), row)
            return self
        if sql.startswith("INSERT INTO advisory_copilot_run_idempotency"):
            row = {
                "idempotency_key": args[0],
                "request_hash": args[1],
                "run_id": args[2],
                "created_at": args[3],
            }
            self.run_idempotency.setdefault(str(row["idempotency_key"]), row)
            return self
        if sql.startswith("UPDATE advisory_copilot_runs SET"):
            run_id = str(args[-1])
            self.runs[run_id] = dict(zip(_RUN_COLUMNS, (run_id, *args[:-1]), strict=True))
            return self
        if sql.startswith("SELECT * FROM advisory_copilot_runs WHERE proposal_id"):
            self._all = self._list_runs(sql=sql, args=args)
            return self

        if sql.startswith("INSERT INTO advisory_copilot_reviews"):
            row = dict(zip(_REVIEW_COLUMNS, args, strict=True))
            self.reviews.setdefault(str(row["review_id"]), row)
            return self
        if sql.startswith("SELECT * FROM advisory_copilot_reviews WHERE run_id = %s AND"):
            run_id, idempotency_key = str(args[0]), str(args[1])
            self._one = next(
                (
                    review
                    for review in self.reviews.values()
                    if review["run_id"] == run_id and review["idempotency_key"] == idempotency_key
                ),
                None,
            )
            return self
        if sql.startswith("SELECT * FROM advisory_copilot_reviews WHERE run_id"):
            run_id = str(args[0])
            self._all = sorted(
                [review for review in self.reviews.values() if review["run_id"] == run_id],
                key=lambda review: (review["occurred_at"], review["review_id"]),
            )
            return self

        raise AssertionError(f"Unhandled SQL in fake Postgres connection: {sql}")

    def fetchone(self) -> dict[str, Any] | None:
        return self._one

    def fetchall(self) -> list[dict[str, Any]]:
        return self._all

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        return None

    def _list_runs(self, *, sql: str, args: tuple[Any, ...]) -> list[dict[str, Any]]:
        proposal_id = str(args[0])
        rows = [row for row in self.runs.values() if row["proposal_id"] == proposal_id]
        arg_index = 1
        if "proposal_version_id" in sql:
            proposal_version_id = args[arg_index]
            arg_index += 1
            rows = [
                row
                for row in rows
                if _json_value(row["lineage_json"])["proposal_version_id"] == proposal_version_id
            ]
        elif "proposal_version_no" in sql:
            proposal_version_no = str(args[arg_index])
            arg_index += 1
            rows = [
                row
                for row in rows
                if str(_json_value(row["lineage_json"])["proposal_version_no"])
                == proposal_version_no
            ]
        if "created_at <" in sql:
            cursor_created_at = str(args[arg_index])
            cursor_run_id = str(args[arg_index + 2])
            arg_index += 3
            rows = [
                row
                for row in rows
                if (row["created_at"], row["run_id"]) < (cursor_created_at, cursor_run_id)
            ]
        limit = int(args[arg_index])
        return sorted(rows, key=lambda row: (row["created_at"], row["run_id"]), reverse=True)[
            :limit
        ]


def _postgres_repository(connection: _FakePostgresConnection) -> PostgresAdvisoryCopilotRepository:
    repository = object.__new__(PostgresAdvisoryCopilotRepository)
    repository._dsn = "postgresql://fake-advisory-copilot"  # noqa: SLF001
    repository._connect = lambda: connection  # noqa: SLF001
    return repository


def _json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


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
    idempotency_key: str | None = "copilot-action-idem-001",
    user_instruction: str = "Summarize the advisory evidence for internal review.",
    created_at: datetime | None = None,
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
            "model_version": "lotus-ai-governed-model.v1",
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
        idempotency_key=idempotency_key,
        requested_intents=("explain_policy_posture",),
        user_instruction=user_instruction,
        created_at=created_at or datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
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

    runs, next_cursor = repository.list_runs_for_proposal_version(
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id=None,
        proposal_version_no=1,
        limit=25,
        cursor=None,
    )
    assert [run.run_id for run in runs] == [result.run.run_id]
    assert next_cursor is None


def test_copilot_persistence_records_normalize_and_bound_audit_identifiers() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    result = _persist_run(repository)

    normalized_run = AdvisoryCopilotRunRecord(
        **{
            **result.run.model_dump(),
            "run_id": "  copilot_run_trimmed  ",
            "idempotency_key": "  copilot-action-idem-trimmed  ",
        }
    )
    assert normalized_run.run_id == "copilot_run_trimmed"
    assert normalized_run.idempotency_key == "copilot-action-idem-trimmed"

    with pytest.raises(ValidationError):
        AdvisoryCopilotRunRecord(**{**result.run.model_dump(), "correlation_id": "x" * 129})
    normalized_guidance = AdvisoryCopilotRunRecord(
        **{
            **result.run.model_dump(),
            "review_guidance_json": ["  Review source evidence before internal use.  "],
            "guardrail_results_json": ["  CLIENT_READY_PUBLICATION_FORBIDDEN  "],
        }
    )
    assert normalized_guidance.review_guidance_json == [
        "Review source evidence before internal use."
    ]
    assert normalized_guidance.guardrail_results_json == ["CLIENT_READY_PUBLICATION_FORBIDDEN"]
    with pytest.raises(ValidationError):
        AdvisoryCopilotRunRecord(
            **{
                **result.run.model_dump(),
                "output_sections_json": [
                    {"section_key": f"SECTION_{index}"} for index in range(65)
                ],
            }
        )
    with pytest.raises(ValidationError):
        AdvisoryCopilotRunRecord(
            **{
                **result.run.model_dump(),
                "review_guidance_json": [f"Guidance {index}" for index in range(17)],
            }
        )
    with pytest.raises(ValidationError):
        AdvisoryCopilotRunRecord(
            **{
                **result.run.model_dump(),
                "guardrail_results_json": ["x" * 161],
            }
        )
    with pytest.raises(ValidationError):
        AdvisoryCopilotRunRecord(
            **{
                **result.run.model_dump(),
                "lineage_json": {f"key_{index}": index for index in range(65)},
            }
        )

    packet_record = save_advisory_copilot_evidence_packet(
        repository=repository,
        evidence_packet=_packet(),
        audience="ADVISOR",
        created_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
        correlation_id="corr_rfc0027_packet_001",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
    )
    normalized_packet = AdvisoryCopilotEvidencePacketRecord(
        **{
            **packet_record.model_dump(),
            "evidence_packet_id": "  copilot_packet_trimmed  ",
            "proposal_id": "  proposal_trimmed  ",
        }
    )
    assert normalized_packet.evidence_packet_id == "copilot_packet_trimmed"
    assert normalized_packet.proposal_id == "proposal_trimmed"
    with pytest.raises(ValidationError):
        AdvisoryCopilotEvidencePacketRecord(
            **{**packet_record.model_dump(), "evidence_packet_id": "x" * 161}
        )
    with pytest.raises(ValidationError):
        AdvisoryCopilotEvidencePacketRecord(
            **{
                **packet_record.model_dump(),
                "reason_json": {f"key_{index}": index for index in range(65)},
            }
        )

    idempotency = AdvisoryCopilotRunIdempotencyRecord(
        idempotency_key="  copilot-action-idem-trimmed  ",
        request_hash=result.run.request_hash,
        run_id=result.run.run_id,
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
    )
    assert idempotency.idempotency_key == "copilot-action-idem-trimmed"
    with pytest.raises(ValidationError):
        AdvisoryCopilotRunIdempotencyRecord(
            idempotency_key="x" * 129,
            request_hash=result.run.request_hash,
            run_id=result.run.run_id,
            created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
        )

    review = record_advisory_copilot_review(
        repository=repository,
        run_id=result.run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        actor_id="supervisor_123",
        reason={"decision": "Reviewed against source evidence."},
        correlation_id="corr_rfc0027_review_001",
        idempotency_key="copilot-review-idem-001",
        occurred_at=datetime(2026, 5, 28, 9, 10, tzinfo=timezone.utc),
    ).review
    normalized_review = AdvisoryCopilotReviewRecord(
        **{
            **review.model_dump(),
            "review_id": "  copilot_review_trimmed  ",
            "idempotency_key": "  copilot-review-idem-trimmed  ",
        }
    )
    assert normalized_review.review_id == "copilot_review_trimmed"
    assert normalized_review.idempotency_key == "copilot-review-idem-trimmed"
    with pytest.raises(ValidationError):
        AdvisoryCopilotReviewRecord(**{**review.model_dump(), "actor_id": "x" * 129})
    with pytest.raises(ValidationError):
        AdvisoryCopilotReviewRecord(
            **{
                **review.model_dump(),
                "reason_json": {f"key_{index}": index for index in range(65)},
            }
        )


def test_copilot_run_listing_is_bounded_and_keyset_paginated() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    first = _persist_run(
        repository,
        idempotency_key="copilot-action-idem-001",
        user_instruction="First internal review request.",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
    ).run
    second = _persist_run(
        repository,
        idempotency_key="copilot-action-idem-002",
        user_instruction="Second internal review request.",
        created_at=datetime(2026, 5, 28, 9, 1, tzinfo=timezone.utc),
    ).run
    third = _persist_run(
        repository,
        idempotency_key="copilot-action-idem-003",
        user_instruction="Third internal review request.",
        created_at=datetime(2026, 5, 28, 9, 2, tzinfo=timezone.utc),
    ).run

    page_one, next_cursor = repository.list_runs_for_proposal_version(
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id=None,
        proposal_version_no=1,
        limit=2,
        cursor=None,
    )
    page_two, final_cursor = repository.list_runs_for_proposal_version(
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id=None,
        proposal_version_no=1,
        limit=2,
        cursor=next_cursor,
    )

    assert [run.run_id for run in page_one] == [third.run_id, second.run_id]
    assert next_cursor is not None
    assert [run.run_id for run in page_two] == [first.run_id]
    assert final_cursor is None


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
            "model_version": "lotus-ai-governed-model.v1",
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


def test_copilot_persistence_rejects_oversized_structured_payloads() -> None:
    repository = InMemoryAdvisoryCopilotRepository()

    with pytest.raises(ValueError, match="COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE"):
        persist_advisory_copilot_run(
            repository=repository,
            evidence_packet=_packet(),
            audience="ADVISOR",
            requested_outputs=("advisor_review_summary",),
            requested_by="advisor_123",
            reason={"business_reason": "x" * 4001},
            draft_status="REVIEW_REQUIRED",
            output_sections=(),
            lineage={"workflow_pack_id": "advisory_copilot_proposal_explanation.pack"},
            review_guidance=(),
            guardrail_reasons=(),
            correlation_id="corr_rfc0027_copilot_001",
        )

    with pytest.raises(ValueError, match="COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE"):
        persist_advisory_copilot_run(
            repository=repository,
            evidence_packet=_packet(),
            audience="ADVISOR",
            requested_outputs=("advisor_review_summary",),
            requested_by="advisor_123",
            reason={"business_reason": "Prepare advisor review."},
            draft_status="REVIEW_REQUIRED",
            output_sections=({"section_key": "SUMMARY", "items": list(range(65))},),
            lineage={"workflow_pack_id": "advisory_copilot_proposal_explanation.pack"},
            review_guidance=(),
            guardrail_reasons=(),
            correlation_id="corr_rfc0027_copilot_001",
        )


def test_in_memory_repository_rejects_direct_conflicts_and_missing_updates() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    run = _persist_run(repository).run

    with pytest.raises(ValueError, match="COPILOT_RUN_HASH_CONFLICT"):
        repository.save_run_with_idempotency(
            run=run.model_copy(update={"request_hash": "sha256:different-request"}),
            idempotency=None,
        )

    missing_run = run.model_copy(update={"run_id": "copilot_run_missing"})
    with pytest.raises(ValueError, match="COPILOT_RUN_NOT_FOUND"):
        repository.update_run(missing_run)

    orphan_key = "copilot-action-idem-orphan"
    repository.save_run_with_idempotency(
        run=run.model_copy(update={"run_id": "copilot_run_orphan_source"}),
        idempotency=AdvisoryCopilotRunIdempotencyRecord(
            idempotency_key=orphan_key,
            request_hash="sha256:orphan-request",
            run_id="copilot_run_orphan_source",
            created_at=datetime(2026, 5, 28, 9, 10, tzinfo=timezone.utc),
        ),
    )
    del repository._runs["copilot_run_orphan_source"]  # noqa: SLF001

    with pytest.raises(ValueError, match="COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED"):
        repository.save_run_with_idempotency(
            run=run.model_copy(update={"run_id": "copilot_run_orphan_source"}),
            idempotency=AdvisoryCopilotRunIdempotencyRecord(
                idempotency_key=orphan_key,
                request_hash="sha256:orphan-request",
                run_id="copilot_run_orphan_source",
                created_at=datetime(2026, 5, 28, 9, 11, tzinfo=timezone.utc),
            ),
        )


def test_in_memory_repository_refreshes_source_projection_packet_only_when_safe() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    reason = {
        "source_projection": "PROPOSAL_VERSION",
        "proposal_id": "proposal_sg_structured_note_001",
        "proposal_version_no": 1,
    }
    record = AdvisoryCopilotEvidencePacketRecord(
        evidence_packet_id="copilot_packet_source_projection_001",
        evidence_packet_hash="sha256:source-projection-001",
        action_family="PROPOSAL_EXPLANATION",
        audience="ADVISOR",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proposal_id="proposal_sg_structured_note_001",
        created_by="advisor_123",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
        correlation_id="corr_rfc0027_packet_001",
        packet_json={"evidence_packet_id": "copilot_packet_source_projection_001"},
        reason_json=reason,
    )

    repository.save_evidence_packet(record)
    same_hash = repository.save_evidence_packet(record)
    refreshed = repository.save_evidence_packet(
        record.model_copy(update={"evidence_packet_hash": "sha256:source-projection-002"})
    )

    assert same_hash.evidence_packet_hash == "sha256:source-projection-001"
    assert refreshed.evidence_packet_hash == "sha256:source-projection-002"

    with pytest.raises(ValueError, match="COPILOT_EVIDENCE_PACKET_HASH_CONFLICT"):
        repository.save_evidence_packet(
            record.model_copy(
                update={
                    "evidence_packet_hash": "sha256:source-projection-003",
                    "reason_json": {"business_reason": "Different packet source."},
                }
            )
        )


def test_in_memory_repository_rejects_review_idempotency_conflicts() -> None:
    repository = InMemoryAdvisoryCopilotRepository()
    run = _persist_run(repository).run
    review = AdvisoryCopilotReviewRecord(
        review_id="copilot_review_001",
        run_id=run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        previous_posture="REVIEW_REQUIRED",
        new_posture="APPROVED_FOR_INTERNAL_USE",
        actor_id="supervisor_123",
        occurred_at=datetime(2026, 5, 28, 9, 5, tzinfo=timezone.utc),
        reason_json={"decision": "Reviewed against cited source evidence."},
        request_hash="sha256:review-request-001",
        idempotency_key="copilot-review-idem-direct",
        correlation_id="corr_rfc0027_review_001",
    )

    repository.append_review(review)
    repository.append_review(review)

    with pytest.raises(ValueError, match="COPILOT_REVIEW_IDEMPOTENCY_KEY_CONFLICT"):
        repository.append_review(
            review.model_copy(
                update={
                    "review_id": "copilot_review_002",
                    "request_hash": "sha256:review-request-002",
                }
            )
        )

    repository._review_idempotency[(run.run_id, "missing-review")] = "copilot_review_missing"  # noqa: SLF001
    assert (
        repository.get_review_by_idempotency(
            run_id=run.run_id,
            idempotency_key="missing-review",
        )
        is None
    )


def test_postgres_repository_round_trips_copilot_run_review_and_keyset_pages() -> None:
    connection = _FakePostgresConnection()
    repository = _postgres_repository(connection)

    saved_packet = save_advisory_copilot_evidence_packet(
        repository=repository,
        evidence_packet=_packet(),
        audience="ADVISOR",
        created_by="advisor_123",
        reason={"business_reason": "Prepare advisor review."},
        correlation_id="corr_rfc0027_packet_001",
        created_at=datetime(2026, 5, 28, 8, 55, tzinfo=timezone.utc),
    )
    loaded_packet = load_advisory_copilot_evidence_packet(
        repository=repository,
        evidence_packet_id=saved_packet.evidence_packet_id,
    )
    first = _persist_run(
        repository,
        idempotency_key="postgres-copilot-action-idem-001",
        user_instruction="First internal review request.",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
    )
    replay = _persist_run(
        repository,
        idempotency_key="postgres-copilot-action-idem-001",
        user_instruction="First internal review request.",
        created_at=datetime(2026, 5, 28, 9, 1, tzinfo=timezone.utc),
    )
    second = _persist_run(
        repository,
        idempotency_key="postgres-copilot-action-idem-002",
        user_instruction="Second internal review request.",
        created_at=datetime(2026, 5, 28, 9, 2, tzinfo=timezone.utc),
    ).run
    third = _persist_run(
        repository,
        idempotency_key="postgres-copilot-action-idem-003",
        user_instruction="Third internal review request.",
        created_at=datetime(2026, 5, 28, 9, 3, tzinfo=timezone.utc),
    ).run

    page_one, next_cursor = repository.list_runs_for_proposal_version(
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id=None,
        proposal_version_no=1,
        limit=2,
        cursor=None,
    )
    page_two, final_cursor = repository.list_runs_for_proposal_version(
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id=None,
        proposal_version_no=1,
        limit=2,
        cursor=next_cursor,
    )
    review = record_advisory_copilot_review(
        repository=repository,
        run_id=first.run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        actor_id="supervisor_123",
        reason={"decision": "Reviewed against cited source evidence."},
        correlation_id="corr_rfc0027_review_001",
        idempotency_key="postgres-copilot-review-idem-001",
        occurred_at=datetime(2026, 5, 28, 9, 5, tzinfo=timezone.utc),
    )
    replayed_review = record_advisory_copilot_review(
        repository=repository,
        run_id=first.run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        actor_id="supervisor_123",
        reason={"decision": "Reviewed against cited source evidence."},
        correlation_id="corr_rfc0027_review_001",
        idempotency_key="postgres-copilot-review-idem-001",
        occurred_at=datetime(2026, 5, 28, 9, 6, tzinfo=timezone.utc),
    )

    assert loaded_packet.evidence_packet_id == "copilot_packet_pb_sg_001"
    assert replay.replayed is True
    assert replay.run.run_id == first.run.run_id
    assert [run.run_id for run in page_one] == [third.run_id, second.run_id]
    assert next_cursor is not None
    assert [run.run_id for run in page_two] == [first.run.run_id]
    assert final_cursor is None
    assert review.replayed is False
    assert replayed_review.replayed is True
    assert repository.get_run(run_id=first.run.run_id).review_posture == (
        "APPROVED_FOR_INTERNAL_USE"
    )
    assert [item.review_id for item in repository.list_reviews(run_id=first.run.run_id)] == [
        review.review.review_id
    ]


def test_postgres_repository_rejects_idempotency_conflicts_and_orphans() -> None:
    connection = _FakePostgresConnection()
    repository = _postgres_repository(connection)
    run = _persist_run(
        repository,
        idempotency_key="postgres-copilot-action-idem-001",
    ).run

    with pytest.raises(ValueError, match="COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT"):
        _persist_run(
            repository,
            idempotency_key="postgres-copilot-action-idem-001",
            user_instruction="Changed internal review request.",
        )

    orphan_key = "postgres-copilot-action-idem-orphan"
    repository.save_run_with_idempotency(
        run=run.model_copy(update={"run_id": "copilot_run_orphan_source"}),
        idempotency=AdvisoryCopilotRunIdempotencyRecord(
            idempotency_key=orphan_key,
            request_hash="sha256:orphan-request",
            run_id="copilot_run_orphan_source",
            created_at=datetime(2026, 5, 28, 9, 10, tzinfo=timezone.utc),
        ),
    )
    del connection.runs["copilot_run_orphan_source"]

    with pytest.raises(ValueError, match="COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED"):
        repository.save_run_with_idempotency(
            run=run.model_copy(update={"run_id": "copilot_run_orphan_attempt"}),
            idempotency=AdvisoryCopilotRunIdempotencyRecord(
                idempotency_key=orphan_key,
                request_hash="sha256:orphan-request",
                run_id="copilot_run_orphan_attempt",
                created_at=datetime(2026, 5, 28, 9, 11, tzinfo=timezone.utc),
            ),
        )


def test_postgres_repository_refreshes_source_projection_packet_only_when_safe() -> None:
    connection = _FakePostgresConnection()
    repository = _postgres_repository(connection)
    source_projection_reason = {
        "source_projection": "PROPOSAL_VERSION",
        "proposal_id": "proposal_sg_structured_note_001",
        "proposal_version_no": 1,
    }
    record = AdvisoryCopilotEvidencePacketRecord(
        evidence_packet_id="copilot_packet_source_projection_001",
        evidence_packet_hash="sha256:source-projection-001",
        action_family="PROPOSAL_EXPLANATION",
        audience="ADVISOR",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        proposal_id="proposal_sg_structured_note_001",
        created_by="advisor_123",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
        correlation_id="corr_rfc0027_packet_001",
        packet_json={"evidence_packet_id": "copilot_packet_source_projection_001"},
        reason_json=source_projection_reason,
    )

    repository.save_evidence_packet(record)
    refreshed = repository.save_evidence_packet(
        record.model_copy(update={"evidence_packet_hash": "sha256:source-projection-002"})
    )

    assert refreshed.evidence_packet_hash == "sha256:source-projection-002"

    with pytest.raises(ValueError, match="COPILOT_EVIDENCE_PACKET_HASH_CONFLICT"):
        repository.save_evidence_packet(
            record.model_copy(
                update={
                    "evidence_packet_hash": "sha256:source-projection-003",
                    "reason_json": {"business_reason": "Different packet source."},
                }
            )
        )


def test_postgres_repository_constructor_reports_missing_dsn_and_driver(monkeypatch) -> None:
    import src.infrastructure.advisory_copilot.postgres as postgres_module

    with pytest.raises(RuntimeError, match="ADVISORY_COPILOT_POSTGRES_DSN_REQUIRED"):
        PostgresAdvisoryCopilotRepository(dsn="")

    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: None)

    with pytest.raises(RuntimeError, match="ADVISORY_COPILOT_POSTGRES_DRIVER_MISSING"):
        PostgresAdvisoryCopilotRepository(dsn="postgresql://missing-driver")
