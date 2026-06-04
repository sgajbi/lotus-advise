from __future__ import annotations

from contextlib import closing
from datetime import datetime
from importlib.util import find_spec
from typing import Any

from src.core.advisory_copilot.idempotency_records import AdvisoryCopilotRunIdempotencyRecord
from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord
from src.core.advisory_copilot.pagination import (
    decode_copilot_run_cursor,
    encode_copilot_run_cursor,
)
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.infrastructure.advisory_copilot.postgres_records import (
    can_refresh_source_projection_packet,
    evidence_packet_from_row,
    json_dump,
    review_from_row,
    run_from_row,
    run_values,
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
                    if not can_refresh_source_projection_packet(
                        existing=evidence_packet_from_row(existing),
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
                            json_dump(record.packet_json),
                            json_dump(record.reason_json),
                            record.evidence_packet_id,
                        ),
                    )
                    connection.commit()
                    return record
                return evidence_packet_from_row(existing)
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
                    json_dump(record.packet_json),
                    json_dump(record.reason_json),
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
        return evidence_packet_from_row(row) if row is not None else None

    def get_run(self, *, run_id: str) -> AdvisoryCopilotRunRecord | None:
        query = "SELECT * FROM advisory_copilot_runs WHERE run_id = %s"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (run_id,)).fetchone()
        return run_from_row(row) if row is not None else None

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
                    return run_from_row(row)
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
                run_values(run)[1:] + (run.run_id,),
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
                    json_dump(review.reason_json),
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
        return review_from_row(row) if row is not None else None

    def list_reviews(self, *, run_id: str) -> list[AdvisoryCopilotReviewRecord]:
        query = """
            SELECT *
            FROM advisory_copilot_reviews
            WHERE run_id = %s
            ORDER BY occurred_at ASC, review_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (run_id,)).fetchall()
        return [review_from_row(row) for row in rows]

    def list_runs_for_proposal_version(
        self,
        *,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[AdvisoryCopilotRunRecord], str | None]:
        decoded_cursor = decode_copilot_run_cursor(cursor)
        clauses = ["proposal_id = %s"]
        params: list[Any] = [proposal_id]
        if proposal_version_id is not None:
            clauses.append("(lineage_json::jsonb ->> 'proposal_version_id') = %s")
            params.append(proposal_version_id)
        elif proposal_version_no is not None:
            clauses.append("(lineage_json::jsonb ->> 'proposal_version_no') = %s")
            params.append(str(proposal_version_no))
        if decoded_cursor is not None:
            cursor_created_at = decoded_cursor.created_at.isoformat()
            clauses.append("(created_at < %s OR (created_at = %s AND run_id < %s))")
            params.extend(
                [
                    cursor_created_at,
                    cursor_created_at,
                    decoded_cursor.run_id,
                ]
            )
        params.append(limit + 1)
        query = f"""
            SELECT *
            FROM advisory_copilot_runs
            WHERE {" AND ".join(clauses)}
            ORDER BY created_at DESC, run_id DESC
            LIMIT %s
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        runs = [run_from_row(row) for row in rows]
        page = runs[:limit]
        next_cursor = encode_copilot_run_cursor(page[-1]) if len(runs) > limit and page else None
        return page, next_cursor

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
            run_values(run),
        )
