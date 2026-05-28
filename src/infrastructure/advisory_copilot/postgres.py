from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime
from importlib.util import find_spec
from typing import Any

from src.core.advisory_copilot.records import (
    AdvisoryCopilotEvidencePacketRecord,
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunIdempotencyRecord,
    AdvisoryCopilotRunRecord,
)
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresAdvisoryCopilotRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("ADVISORY_COPILOT_POSTGRES_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("ADVISORY_COPILOT_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_evidence_packet(
        self, record: AdvisoryCopilotEvidencePacketRecord
    ) -> AdvisoryCopilotEvidencePacketRecord:
        query = """
            INSERT INTO advisory_copilot_evidence_packets (
                evidence_packet_id, evidence_packet_hash, action_family, audience, portfolio_id,
                proposal_id, created_by, created_at, correlation_id, packet_json, reason_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (evidence_packet_id) DO NOTHING
        """
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT *
                FROM advisory_copilot_evidence_packets
                WHERE evidence_packet_id = %s
                """,
                (record.evidence_packet_id,),
            ).fetchone()
            if existing is not None:
                if existing["evidence_packet_hash"] != record.evidence_packet_hash:
                    if not _can_refresh_source_projection_packet(
                        existing=_evidence_packet_from_row(existing),
                        incoming=record,
                    ):
                        raise ValueError("COPILOT_EVIDENCE_PACKET_HASH_CONFLICT")
                    connection.execute(
                        """
                        UPDATE advisory_copilot_evidence_packets
                        SET evidence_packet_hash = %s,
                            action_family = %s,
                            audience = %s,
                            portfolio_id = %s,
                            proposal_id = %s,
                            created_by = %s,
                            created_at = %s,
                            correlation_id = %s,
                            packet_json = %s,
                            reason_json = %s
                        WHERE evidence_packet_id = %s
                        """,
                        (
                            record.evidence_packet_hash,
                            record.action_family,
                            record.audience,
                            record.portfolio_id,
                            record.proposal_id,
                            record.created_by,
                            record.created_at.isoformat(),
                            record.correlation_id,
                            _json_dump(record.packet_json),
                            _json_dump(record.reason_json),
                            record.evidence_packet_id,
                        ),
                    )
                    connection.commit()
                    return record
                return _evidence_packet_from_row(existing)
            connection.execute(
                query,
                (
                    record.evidence_packet_id,
                    record.evidence_packet_hash,
                    record.action_family,
                    record.audience,
                    record.portfolio_id,
                    record.proposal_id,
                    record.created_by,
                    record.created_at.isoformat(),
                    record.correlation_id,
                    _json_dump(record.packet_json),
                    _json_dump(record.reason_json),
                ),
            )
            connection.commit()
        return record

    def get_evidence_packet(
        self, *, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketRecord | None:
        query = """
            SELECT *
            FROM advisory_copilot_evidence_packets
            WHERE evidence_packet_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (evidence_packet_id,)).fetchone()
        return _evidence_packet_from_row(row) if row is not None else None

    def get_run(self, *, run_id: str) -> AdvisoryCopilotRunRecord | None:
        query = "SELECT * FROM advisory_copilot_runs WHERE run_id = %s"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (run_id,)).fetchone()
        return _run_from_row(row) if row is not None else None

    def get_run_idempotency(
        self, *, idempotency_key: str
    ) -> AdvisoryCopilotRunIdempotencyRecord | None:
        query = """
            SELECT idempotency_key, request_hash, run_id, created_at
            FROM advisory_copilot_run_idempotency
            WHERE idempotency_key = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (idempotency_key,)).fetchone()
        if row is None:
            return None
        return AdvisoryCopilotRunIdempotencyRecord(
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            run_id=row["run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_run_with_idempotency(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord:
        with closing(self._connect()) as connection:
            if idempotency is not None:
                existing = connection.execute(
                    """
                    SELECT idempotency_key, request_hash, run_id, created_at
                    FROM advisory_copilot_run_idempotency
                    WHERE idempotency_key = %s
                    """,
                    (idempotency.idempotency_key,),
                ).fetchone()
                if existing is not None:
                    if existing["request_hash"] != idempotency.request_hash:
                        raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
                    row = connection.execute(
                        "SELECT * FROM advisory_copilot_runs WHERE run_id = %s",
                        (existing["run_id"],),
                    ).fetchone()
                    if row is None:
                        raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")
                    return _run_from_row(row)
            self._insert_run(connection=connection, run=run)
            if idempotency is not None:
                connection.execute(
                    """
                    INSERT INTO advisory_copilot_run_idempotency (
                        idempotency_key, request_hash, run_id, created_at
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    (
                        idempotency.idempotency_key,
                        idempotency.request_hash,
                        idempotency.run_id,
                        idempotency.created_at.isoformat(),
                    ),
                )
            connection.commit()
        return run

    def update_run(self, run: AdvisoryCopilotRunRecord) -> None:
        query = """
            UPDATE advisory_copilot_runs
            SET schema_version = %s,
                action_family = %s,
                audience = %s,
                portfolio_id = %s,
                proposal_id = %s,
                evidence_packet_id = %s,
                evidence_packet_hash = %s,
                request_hash = %s,
                output_hash = %s,
                review_posture = %s,
                client_ready_publication = %s,
                retention_class = %s,
                legal_hold = %s,
                retention_expires_at = %s,
                created_by = %s,
                caller_app = %s,
                tenant_id = %s,
                correlation_id = %s,
                idempotency_key = %s,
                created_at = %s,
                updated_at = %s,
                lotus_ai_workflow_run_id = %s,
                lotus_ai_model_version = %s,
                workflow_pack_id = %s,
                workflow_pack_version = %s,
                prompt_template_version = %s,
                output_schema_version = %s,
                evaluation_pack_ref = %s,
                evidence_packet_json = %s,
                request_summary_json = %s,
                output_sections_json = %s,
                review_guidance_json = %s,
                guardrail_results_json = %s,
                lineage_json = %s
            WHERE run_id = %s
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                _run_values(run)[1:] + (run.run_id,),
            )
            connection.commit()

    def append_review(self, review: AdvisoryCopilotReviewRecord) -> None:
        query = """
            INSERT INTO advisory_copilot_reviews (
                review_id, run_id, schema_version, action, previous_posture, new_posture,
                actor_id, occurred_at, reason_json, request_hash, idempotency_key, correlation_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (review_id) DO NOTHING
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    review.review_id,
                    review.run_id,
                    review.schema_version,
                    review.action,
                    review.previous_posture,
                    review.new_posture,
                    review.actor_id,
                    review.occurred_at.isoformat(),
                    _json_dump(review.reason_json),
                    review.request_hash,
                    review.idempotency_key,
                    review.correlation_id,
                ),
            )
            connection.commit()

    def get_review_by_idempotency(
        self, *, run_id: str, idempotency_key: str
    ) -> AdvisoryCopilotReviewRecord | None:
        query = """
            SELECT *
            FROM advisory_copilot_reviews
            WHERE run_id = %s AND idempotency_key = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (run_id, idempotency_key)).fetchone()
        return _review_from_row(row) if row is not None else None

    def list_reviews(self, *, run_id: str) -> list[AdvisoryCopilotReviewRecord]:
        query = """
            SELECT *
            FROM advisory_copilot_reviews
            WHERE run_id = %s
            ORDER BY occurred_at ASC, review_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (run_id,)).fetchall()
        return [_review_from_row(row) for row in rows]

    def list_runs_for_proposal_version(
        self,
        *,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
    ) -> list[AdvisoryCopilotRunRecord]:
        query = """
            SELECT *
            FROM advisory_copilot_runs
            WHERE proposal_id = %s
            ORDER BY created_at DESC, run_id DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_id,)).fetchall()
        runs = [_run_from_row(row) for row in rows]
        return [
            run
            for run in runs
            if _matches_proposal_version(
                run=run,
                proposal_version_id=proposal_version_id,
                proposal_version_no=proposal_version_no,
            )
        ]

    def _connect(self) -> Any:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="advisory_copilot")

    def _insert_run(self, *, connection: Any, run: AdvisoryCopilotRunRecord) -> None:
        connection.execute(
            """
            INSERT INTO advisory_copilot_runs (
                run_id, schema_version, action_family, audience, portfolio_id, proposal_id,
                evidence_packet_id, evidence_packet_hash, request_hash, output_hash,
                review_posture, client_ready_publication, retention_class, legal_hold,
                retention_expires_at, created_by, caller_app, tenant_id, correlation_id,
                idempotency_key, created_at, updated_at, lotus_ai_workflow_run_id,
                lotus_ai_model_version, workflow_pack_id, workflow_pack_version,
                prompt_template_version, output_schema_version, evaluation_pack_ref,
                evidence_packet_json, request_summary_json, output_sections_json,
                review_guidance_json, guardrail_results_json, lineage_json
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (run_id) DO NOTHING
            """,
            _run_values(run),
        )


def _run_values(run: AdvisoryCopilotRunRecord) -> tuple[Any, ...]:
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
        _json_dump(run.evidence_packet_json),
        _json_dump(run.request_summary_json),
        _json_dump(run.output_sections_json),
        _json_dump(run.review_guidance_json),
        _json_dump(run.guardrail_results_json),
        _json_dump(run.lineage_json),
    )


def _run_from_row(row: dict[str, Any]) -> AdvisoryCopilotRunRecord:
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
        retention_expires_at=_optional_datetime(row["retention_expires_at"]),
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
        evidence_packet_json=_json_load(row["evidence_packet_json"]),
        request_summary_json=_json_load(row["request_summary_json"]),
        output_sections_json=_json_load(row["output_sections_json"]),
        review_guidance_json=_json_load(row["review_guidance_json"]),
        guardrail_results_json=_json_load(row["guardrail_results_json"]),
        lineage_json=_json_load(row["lineage_json"]),
    )


def _evidence_packet_from_row(row: dict[str, Any]) -> AdvisoryCopilotEvidencePacketRecord:
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
        packet_json=_json_load(row["packet_json"]),
        reason_json=_json_load(row["reason_json"]),
    )


def _review_from_row(row: dict[str, Any]) -> AdvisoryCopilotReviewRecord:
    return AdvisoryCopilotReviewRecord(
        review_id=row["review_id"],
        run_id=row["run_id"],
        schema_version=row["schema_version"],
        action=row["action"],
        previous_posture=row["previous_posture"],
        new_posture=row["new_posture"],
        actor_id=row["actor_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        reason_json=_json_load(row["reason_json"]),
        request_hash=row["request_hash"],
        idempotency_key=row["idempotency_key"],
        correlation_id=row["correlation_id"],
    )


def _json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json_load(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _optional_datetime(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) and value else None


def _matches_proposal_version(
    *,
    run: AdvisoryCopilotRunRecord,
    proposal_version_id: str | None,
    proposal_version_no: int | None,
) -> bool:
    if proposal_version_id is not None:
        return run.lineage_json.get("proposal_version_id") == proposal_version_id
    if proposal_version_no is not None:
        return run.lineage_json.get("proposal_version_no") == proposal_version_no
    return True


def _can_refresh_source_projection_packet(
    *,
    existing: AdvisoryCopilotEvidencePacketRecord,
    incoming: AdvisoryCopilotEvidencePacketRecord,
) -> bool:
    return (
        existing.reason_json.get("source_projection") == "PROPOSAL_VERSION"
        and incoming.reason_json.get("source_projection") == "PROPOSAL_VERSION"
        and existing.reason_json.get("proposal_id") == incoming.reason_json.get("proposal_id")
        and existing.reason_json.get("proposal_version_no")
        == incoming.reason_json.get("proposal_version_no")
        and existing.action_family == incoming.action_family
        and existing.audience == incoming.audience
        and existing.portfolio_id == incoming.portfolio_id
        and existing.proposal_id == incoming.proposal_id
    )
