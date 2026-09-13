from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime

import pytest

from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.packet_persistence import save_advisory_copilot_evidence_packet
from src.core.advisory_copilot.reference_models import CopilotLineageRef, CopilotSourceRef
from src.core.advisory_copilot.review_authority import CopilotReviewPrincipal
from src.core.advisory_copilot.review_persistence import record_advisory_copilot_review
from src.core.advisory_copilot.run_persistence import persist_advisory_copilot_run
from src.core.advisory_copilot.section_models import CopilotEvidencePacketSection
from src.infrastructure.advisory_copilot.postgres import PostgresAdvisoryCopilotRepository

_DSN = os.getenv("ADVISORY_COPILOT_POSTGRES_INTEGRATION_DSN", "").strip()


def _repository() -> PostgresAdvisoryCopilotRepository:
    if not _DSN:
        pytest.skip(
            "ADVISORY_COPILOT_POSTGRES_INTEGRATION_DSN is required for real PostgreSQL proof"
        )
    return PostgresAdvisoryCopilotRepository(dsn=_DSN)


def _packet(*, tenant_id: str, suffix: str) -> CopilotEvidencePacket:
    packet_id = f"copilot-packet-tenant-{suffix}"
    return CopilotEvidencePacket(
        evidence_packet_id=packet_id,
        evidence_packet_hash=f"sha256:packet-{suffix}",
        action_family="PROPOSAL_EXPLANATION",
        portfolio_id=f"portfolio-{tenant_id}",
        proposal_id=f"proposal-{tenant_id}",
        sections=(
            CopilotEvidencePacketSection(
                section_key="POLICY_POSTURE",
                title="Policy posture",
                evidence_class="COMPLIANCE_REVIEW_EVIDENCE",
                source_refs=(
                    CopilotSourceRef(
                        source_system="lotus-advise",
                        source_type="POLICY_EVALUATION",
                        source_id=f"policy-{suffix}",
                        content_hash=f"sha256:policy-{suffix}",
                        access_class="COMPLIANCE_REVIEW_EVIDENCE",
                    ),
                ),
                summary_items=("Policy review is required before internal use.",),
            ),
        ),
        lineage_refs=(
            CopilotLineageRef(
                lineage_type="EVIDENCE_PACKET",
                lineage_id=packet_id,
                source_system="lotus-advise",
            ),
        ),
        retention_class="ADVISORY_REVIEW_RECORD",
    )


def _persist(
    *, repository: PostgresAdvisoryCopilotRepository, tenant_id: str, suffix: str, key: str
):
    packet = _packet(tenant_id=tenant_id, suffix=suffix)
    save_advisory_copilot_evidence_packet(
        repository=repository,
        evidence_packet=packet,
        audience="ADVISOR",
        tenant_id=tenant_id,
        created_by="advisor-test",
        reason={"business_reason": "Tenant isolation integration proof."},
        correlation_id=f"corr-{suffix}",
        created_at=datetime(2026, 9, 13, tzinfo=UTC),
    )
    return persist_advisory_copilot_run(
        repository=repository,
        evidence_packet=packet,
        audience="ADVISOR",
        requested_outputs=("advisor_review_summary",),
        requested_by="advisor-test",
        reason={"business_reason": "Tenant isolation integration proof."},
        draft_status="REVIEW_REQUIRED",
        output_sections=({"section_key": "SUMMARY", "text": "Review required."},),
        lineage={
            "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
            "workflow_pack_version": "v1",
            "proposal_version_no": 1,
        },
        review_guidance=("Review evidence.",),
        guardrail_reasons=(),
        correlation_id=f"corr-{suffix}",
        tenant_id=tenant_id,
        idempotency_key=key,
        created_at=datetime(2026, 9, 13, tzinfo=UTC),
    ).run


def _review_principal(
    *, tenant_id: str, packet: CopilotEvidencePacket, actor_id: str = "supervisor-test"
) -> CopilotReviewPrincipal:
    return CopilotReviewPrincipal(
        actor_id=actor_id,
        role="COMPLIANCE_REVIEWER",
        tenant_id=tenant_id,
        legal_entity_code="REFERENCE",
        correlation_id=f"corr-review-{tenant_id}",
        service_identity="lotus-gateway",
        capabilities=frozenset({"advisory.copilot.review"}),
        authorized_proposal_id=packet.proposal_id,
        authorized_portfolio_id=packet.portfolio_id,
    )


def test_real_postgres_scopes_copilot_packets_runs_replay_and_reviews_per_tenant() -> None:
    suffix = uuid.uuid4().hex
    sg_tenant = f"tenant-sg-{suffix}"
    hk_tenant = f"tenant-hk-{suffix}"
    shared_key = f"shared-idempotency-{suffix}"

    def persist(tenant_id: str, tenant_suffix: str):
        return _persist(
            repository=_repository(),
            tenant_id=tenant_id,
            suffix=f"{tenant_suffix}-{suffix}",
            key=shared_key,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        sg_run, hk_run = list(
            executor.map(lambda args: persist(*args), ((sg_tenant, "sg"), (hk_tenant, "hk")))
        )

    restarted = _repository()
    assert sg_run.run_id != hk_run.run_id
    assert restarted.get_run(tenant_id=sg_tenant, run_id=sg_run.run_id) is not None
    assert restarted.get_run(tenant_id=hk_tenant, run_id=hk_run.run_id) is not None
    assert restarted.get_run(tenant_id=hk_tenant, run_id=sg_run.run_id) is None
    restarted.update_run(sg_run.model_copy(update={"tenant_id": hk_tenant}))
    assert restarted.get_run(tenant_id=sg_tenant, run_id=sg_run.run_id).tenant_id == sg_tenant
    assert (
        restarted.get_run_idempotency(tenant_id=sg_tenant, idempotency_key=shared_key) is not None
    )
    assert (
        restarted.get_run_idempotency(tenant_id=hk_tenant, idempotency_key=shared_key) is not None
    )

    sg_packet = _packet(tenant_id=sg_tenant, suffix=f"sg-{suffix}")
    assert (
        restarted.get_evidence_packet_for_authorized_scope(
            tenant_id=sg_tenant,
            evidence_packet_id=sg_packet.evidence_packet_id,
            authorized_portfolio_id=sg_packet.portfolio_id,
            authorized_proposal_id=sg_packet.proposal_id,
        )
        is not None
    )
    assert (
        restarted.get_evidence_packet_for_authorized_scope(
            tenant_id=sg_tenant,
            evidence_packet_id=sg_packet.evidence_packet_id,
            authorized_portfolio_id=sg_packet.portfolio_id,
            authorized_proposal_id="proposal-not-authorized",
        )
        is None
    )
    review = record_advisory_copilot_review(
        repository=restarted,
        run_id=sg_run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        principal=_review_principal(tenant_id=sg_tenant, packet=sg_packet),
        submitted_actor_id="supervisor-test",
        reason={"decision": "Reviewed using tenant-owned evidence."},
        correlation_id=f"corr-review-{suffix}",
        idempotency_key=f"review-{suffix}",
    )
    assert review.replayed is False
    assert restarted.list_reviews(tenant_id=hk_tenant, run_id=sg_run.run_id) == []

    with closing(restarted._connect()) as connection:  # noqa: SLF001
        rows = connection.execute(
            """
            SELECT admitted_tenant_id, idempotency_key
            FROM advisory_copilot_runs
            WHERE run_id IN (%s, %s)
            ORDER BY admitted_tenant_id
            """,
            (sg_run.run_id, hk_run.run_id),
        ).fetchall()
    assert {(row["admitted_tenant_id"], row["idempotency_key"]) for row in rows} == {
        (sg_tenant, shared_key),
        (hk_tenant, shared_key),
    }


def test_real_postgres_serializes_same_tenant_copilot_replay_contention() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"tenant-sg-{suffix}"
    key = f"same-tenant-idempotency-{suffix}"

    def persist() -> str:
        return _persist(
            repository=_repository(),
            tenant_id=tenant_id,
            suffix=f"same-{suffix}",
            key=key,
        ).run_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        run_ids = list(executor.map(lambda _: persist(), range(2)))

    assert run_ids[0] == run_ids[1]


def test_real_postgres_review_transition_rolls_back_then_retries_after_restart() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"tenant-sg-{suffix}"
    packet_suffix = f"review-rollback-{suffix}"
    packet = _packet(tenant_id=tenant_id, suffix=packet_suffix)
    repository = _repository()
    run = _persist(
        repository=repository,
        tenant_id=tenant_id,
        suffix=packet_suffix,
        key=f"review-rollback-run-{suffix}",
    )
    function_name = f"copilot_review_fail_{suffix}"
    trigger_name = f"copilot_review_fail_trigger_{suffix}"
    with closing(repository._connect()) as connection:  # noqa: SLF001
        connection.execute(
            f"""
            CREATE FUNCTION {function_name}() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.run_id = '{run.run_id}' THEN
                    RAISE EXCEPTION 'review transition failure injection';
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        connection.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON advisory_copilot_runs
            FOR EACH ROW EXECUTE FUNCTION {function_name}()
            """
        )
        connection.commit()
    try:
        with pytest.raises(Exception, match="review transition failure injection"):
            record_advisory_copilot_review(
                repository=repository,
                run_id=run.run_id,
                action="APPROVE_FOR_INTERNAL_USE",
                principal=_review_principal(tenant_id=tenant_id, packet=packet),
                submitted_actor_id="supervisor-test",
                reason={"decision": "Atomic rollback proof."},
                correlation_id=f"corr-review-rollback-{suffix}",
                idempotency_key=f"review-rollback-{suffix}",
            )
        assert repository.list_reviews(tenant_id=tenant_id, run_id=run.run_id) == []
        assert (
            repository.get_run(tenant_id=tenant_id, run_id=run.run_id).review_posture
            == "REVIEW_REQUIRED"
        )
    finally:
        with closing(repository._connect()) as connection:  # noqa: SLF001
            connection.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON advisory_copilot_runs")
            connection.execute(f"DROP FUNCTION IF EXISTS {function_name}()")
            connection.commit()

    restarted = _repository()
    accepted = record_advisory_copilot_review(
        repository=restarted,
        run_id=run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        principal=_review_principal(tenant_id=tenant_id, packet=packet),
        submitted_actor_id="supervisor-test",
        reason={"decision": "Atomic rollback proof."},
        correlation_id=f"corr-review-rollback-{suffix}",
        idempotency_key=f"review-rollback-{suffix}",
    )
    replay = record_advisory_copilot_review(
        repository=_repository(),
        run_id=run.run_id,
        action="APPROVE_FOR_INTERNAL_USE",
        principal=_review_principal(tenant_id=tenant_id, packet=packet),
        submitted_actor_id="supervisor-test",
        reason={"decision": "Atomic rollback proof."},
        correlation_id=f"corr-review-rollback-{suffix}",
        idempotency_key=f"review-rollback-{suffix}",
    )
    assert accepted.replayed is False
    assert replay.replayed is True
    assert replay.run.review_posture == "APPROVED_FOR_INTERNAL_USE"
    assert len(restarted.list_reviews(tenant_id=tenant_id, run_id=run.run_id)) == 1


def test_real_postgres_serializes_competing_terminal_reviewers() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"tenant-sg-{suffix}"
    packet_suffix = f"review-contention-{suffix}"
    packet = _packet(tenant_id=tenant_id, suffix=packet_suffix)
    run = _persist(
        repository=_repository(),
        tenant_id=tenant_id,
        suffix=packet_suffix,
        key=f"review-contention-run-{suffix}",
    )

    def review(action: str, actor_id: str) -> str:
        try:
            result = record_advisory_copilot_review(
                repository=_repository(),
                run_id=run.run_id,
                action=action,  # type: ignore[arg-type]
                principal=_review_principal(
                    tenant_id=tenant_id,
                    packet=packet,
                    actor_id=actor_id,
                ),
                submitted_actor_id=actor_id,
                reason={"decision": f"{action} under competing terminal review proof."},
                correlation_id=f"corr-{action.lower()}-{suffix}",
                idempotency_key=f"review-{action.lower()}-{suffix}",
            )
            return f"accepted:{result.run.review_posture}"
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                lambda request: review(*request),
                (("APPROVE_FOR_INTERNAL_USE", "supervisor-a"), ("REJECT", "supervisor-b")),
            )
        )

    accepted = [outcome for outcome in outcomes if outcome.startswith("accepted:")]
    rejected = [outcome for outcome in outcomes if not outcome.startswith("accepted:")]
    persisted = _repository()
    reviews = persisted.list_reviews(tenant_id=tenant_id, run_id=run.run_id)
    assert len(accepted) == 1
    assert rejected == ["COPILOT_RUN_REVIEW_POSTURE_TERMINAL"]
    assert len(reviews) == 1
    persisted_run = persisted.get_run(tenant_id=tenant_id, run_id=run.run_id)
    assert persisted_run is not None
    assert persisted_run.review_posture == reviews[0].new_posture
