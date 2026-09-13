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
from src.core.advisory_copilot.review import is_terminal_review_posture
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.source_projection_packets import (
    can_refresh_source_projection_packet,
)
from src.infrastructure.advisory_copilot.postgres_records import (
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
                proposal_id, tenant_id, created_by, created_at, correlation_id,
                packet_json, reason_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, evidence_packet_id) DO NOTHING
            RETURNING evidence_packet_id
        """
        with closing(self._connect()) as connection:
            existing = connection.execute(
                """
                SELECT *
                FROM advisory_copilot_evidence_packets
                WHERE evidence_packet_id = %s AND tenant_id = %s
                """,
                (record.evidence_packet_id, record.tenant_id),
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
                            tenant_id = %s,
                            created_by = %s,
                            created_at = %s,
                            correlation_id = %s,
                            packet_json = %s,
                            reason_json = %s
                        WHERE evidence_packet_id = %s AND tenant_id = %s
                        """,
                        (
                            record.evidence_packet_hash,
                            record.action_family,
                            record.audience,
                            record.portfolio_id,
                            record.proposal_id,
                            record.tenant_id,
                            record.created_by,
                            record.created_at.isoformat(),
                            record.correlation_id,
                            json_dump(record.packet_json),
                            json_dump(record.reason_json),
                            record.evidence_packet_id,
                            record.tenant_id,
                        ),
                    )
                    connection.commit()
                    return record
                return evidence_packet_from_row(existing)
            inserted = connection.execute(
                query,
                (
                    record.evidence_packet_id,
                    record.evidence_packet_hash,
                    record.action_family,
                    record.audience,
                    record.portfolio_id,
                    record.proposal_id,
                    record.tenant_id,
                    record.created_by,
                    record.created_at.isoformat(),
                    record.correlation_id,
                    json_dump(record.packet_json),
                    json_dump(record.reason_json),
                ),
            ).fetchone()
            if inserted is None:
                existing = connection.execute(
                    """
                    SELECT *
                    FROM advisory_copilot_evidence_packets
                    WHERE evidence_packet_id = %s AND tenant_id = %s
                    """,
                    (record.evidence_packet_id, record.tenant_id),
                ).fetchone()
                if existing is None:
                    raise ValueError("COPILOT_EVIDENCE_PACKET_NOT_FOUND")
                if existing["evidence_packet_hash"] != record.evidence_packet_hash:
                    raise ValueError("COPILOT_EVIDENCE_PACKET_HASH_CONFLICT")
                return evidence_packet_from_row(existing)
            connection.commit()
        return record

    def get_evidence_packet(
        self, *, tenant_id: str, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketRecord | None:
        query = """
            SELECT *
            FROM advisory_copilot_evidence_packets
            WHERE evidence_packet_id = %s AND tenant_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (evidence_packet_id, tenant_id)).fetchone()
        return evidence_packet_from_row(row) if row is not None else None

    def get_evidence_packet_for_authorized_scope(
        self,
        *,
        tenant_id: str,
        evidence_packet_id: str,
        authorized_portfolio_id: str | None,
        authorized_proposal_id: str | None,
    ) -> AdvisoryCopilotEvidencePacketRecord | None:
        query = """
            SELECT *
            FROM advisory_copilot_evidence_packets
            WHERE evidence_packet_id = %s
              AND tenant_id = %s
              AND portfolio_id = %s
              AND (proposal_id IS NULL OR proposal_id = %s)
        """
        with closing(self._connect()) as connection:
            row = connection.execute(
                query,
                (
                    evidence_packet_id,
                    tenant_id,
                    authorized_portfolio_id,
                    authorized_proposal_id,
                ),
            ).fetchone()
        return evidence_packet_from_row(row) if row is not None else None

    def get_run(self, *, tenant_id: str, run_id: str) -> AdvisoryCopilotRunRecord | None:
        query = "SELECT * FROM advisory_copilot_runs WHERE run_id = %s AND admitted_tenant_id = %s"
        with closing(self._connect()) as connection:
            row = connection.execute(query, (run_id, tenant_id)).fetchone()
        return run_from_row(row) if row is not None else None

    def get_run_for_authorized_scope(
        self,
        *,
        tenant_id: str,
        run_id: str,
        authorized_portfolio_id: str | None,
        authorized_proposal_id: str | None,
    ) -> AdvisoryCopilotRunRecord | None:
        query = """
            SELECT * FROM advisory_copilot_runs
            WHERE run_id = %s
              AND admitted_tenant_id = %s
              AND portfolio_id = %s
              AND (proposal_id IS NULL OR proposal_id = %s)
        """
        with closing(self._connect()) as connection:
            row = connection.execute(
                query,
                (run_id, tenant_id, authorized_portfolio_id, authorized_proposal_id),
            ).fetchone()
        return run_from_row(row) if row is not None else None

    def get_run_idempotency(
        self, *, tenant_id: str, idempotency_key: str
    ) -> AdvisoryCopilotRunIdempotencyRecord | None:
        query = """
            SELECT tenant_id, idempotency_key, request_hash, run_id, created_at
            FROM advisory_copilot_run_idempotency
            WHERE tenant_id = %s AND idempotency_key = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (tenant_id, idempotency_key)).fetchone()
        if row is None:
            return None
        return AdvisoryCopilotRunIdempotencyRecord(
            tenant_id=row["tenant_id"],
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
            replay = self._find_idempotent_run(connection=connection, idempotency=idempotency)
            if replay is not None:
                return replay
            if not self._insert_run(connection=connection, run=run):
                existing_run = self._require_existing_run(
                    connection=connection, run=run, idempotency=idempotency
                )
                connection.commit()
                return existing_run
            if idempotency is not None and not self._insert_idempotency(
                connection=connection,
                idempotency=idempotency,
            ):
                replay = self._require_idempotent_run(
                    connection=connection,
                    idempotency=idempotency,
                )
                connection.rollback()
                return replay
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
            WHERE run_id = %s AND admitted_tenant_id = %s
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                run_values(run)[1:] + (run.run_id, run.tenant_id),
            )
            connection.commit()

    def transition_review(
        self,
        *,
        expected_run: AdvisoryCopilotRunRecord,
        updated_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> tuple[AdvisoryCopilotRunRecord, AdvisoryCopilotReviewRecord, bool]:
        with closing(self._connect()) as connection:
            try:
                current = self._locked_run_for_review(connection=connection, review=review)
                existing = self._review_for_idempotency(connection=connection, review=review)
                if existing is not None:
                    if existing.request_hash != review.request_hash:
                        raise ValueError("COPILOT_REVIEW_IDEMPOTENCY_KEY_CONFLICT")
                    persisted_run = self._reconcile_existing_review(
                        connection=connection,
                        current=current,
                        expected_run=expected_run,
                        updated_run=updated_run,
                        review=existing,
                    )
                    connection.commit()
                    return persisted_run, existing, True
                self._assert_review_transition_preconditions(
                    current=current,
                    expected_run=expected_run,
                    review=review,
                )
                connection.execute(
                    """
                    INSERT INTO advisory_copilot_reviews (
                        review_id, run_id, schema_version, action, previous_posture, new_posture,
                        tenant_id, actor_id, occurred_at, reason_json, request_hash,
                        idempotency_key, correlation_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    self._review_values(review),
                )
                self._guarded_review_posture_update(
                    connection=connection,
                    current=current,
                    updated_run=updated_run,
                    review=review,
                )
                connection.commit()
                return updated_run, review, False
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _review_values(review: AdvisoryCopilotReviewRecord) -> tuple[Any, ...]:
        return (
            review.review_id,
            review.run_id,
            review.schema_version,
            review.action,
            review.previous_posture,
            review.new_posture,
            review.tenant_id,
            review.actor_id,
            review.occurred_at.isoformat(),
            json_dump(review.reason_json),
            review.request_hash,
            review.idempotency_key,
            review.correlation_id,
        )

    @staticmethod
    def _locked_run_for_review(
        *, connection: Any, review: AdvisoryCopilotReviewRecord
    ) -> AdvisoryCopilotRunRecord:
        row = connection.execute(
            """
            SELECT *
            FROM advisory_copilot_runs
            WHERE run_id = %s AND admitted_tenant_id = %s
            FOR UPDATE
            """,
            (review.run_id, review.tenant_id),
        ).fetchone()
        if row is None:
            raise ValueError("COPILOT_RUN_NOT_FOUND")
        return run_from_row(row)

    @staticmethod
    def _review_for_idempotency(
        *, connection: Any, review: AdvisoryCopilotReviewRecord
    ) -> AdvisoryCopilotReviewRecord | None:
        if review.idempotency_key is None:
            return None
        row = connection.execute(
            """
            SELECT *
            FROM advisory_copilot_reviews
            WHERE tenant_id = %s AND run_id = %s AND idempotency_key = %s
            """,
            (review.tenant_id, review.run_id, review.idempotency_key),
        ).fetchone()
        return review_from_row(row) if row is not None else None

    def _reconcile_existing_review(
        self,
        *,
        connection: Any,
        current: AdvisoryCopilotRunRecord,
        expected_run: AdvisoryCopilotRunRecord,
        updated_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> AdvisoryCopilotRunRecord:
        if current.review_posture == review.new_posture:
            return current
        if (
            current.review_posture == review.previous_posture
            and current.updated_at == expected_run.updated_at
        ):
            self._guarded_review_posture_update(
                connection=connection,
                current=current,
                updated_run=updated_run,
                review=review,
            )
            return updated_run
        raise ValueError("COPILOT_REVIEW_TRANSITION_INCONSISTENT")

    @staticmethod
    def _assert_review_transition_preconditions(
        *,
        current: AdvisoryCopilotRunRecord,
        expected_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> None:
        if is_terminal_review_posture(current.review_posture):
            raise ValueError("COPILOT_RUN_REVIEW_POSTURE_TERMINAL")
        if (
            current.review_posture != expected_run.review_posture
            or current.updated_at != expected_run.updated_at
            or current.review_posture != review.previous_posture
        ):
            raise ValueError("COPILOT_REVIEW_TRANSITION_STALE")

    @staticmethod
    def _guarded_review_posture_update(
        *,
        connection: Any,
        current: AdvisoryCopilotRunRecord,
        updated_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> None:
        result = connection.execute(
            """
            UPDATE advisory_copilot_runs
            SET review_posture = %s, updated_at = %s
            WHERE run_id = %s
              AND admitted_tenant_id = %s
              AND review_posture = %s
              AND updated_at = %s
            """,
            (
                updated_run.review_posture,
                updated_run.updated_at.isoformat(),
                review.run_id,
                review.tenant_id,
                review.previous_posture,
                current.updated_at.isoformat(),
            ),
        )
        if result.rowcount != 1:
            raise ValueError("COPILOT_REVIEW_TRANSITION_STALE")

    def list_reviews(self, *, tenant_id: str, run_id: str) -> list[AdvisoryCopilotReviewRecord]:
        query = """
            SELECT *
            FROM advisory_copilot_reviews
            WHERE tenant_id = %s AND run_id = %s
            ORDER BY occurred_at ASC, review_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (tenant_id, run_id)).fetchall()
        return [review_from_row(row) for row in rows]

    def list_runs_for_proposal_version(
        self,
        *,
        tenant_id: str,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[AdvisoryCopilotRunRecord], str | None]:
        decoded_cursor = decode_copilot_run_cursor(cursor)
        clauses = ["admitted_tenant_id = %s", "proposal_id = %s"]
        params: list[Any] = [tenant_id, proposal_id]
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

    def _insert_run(self, *, connection: Any, run: AdvisoryCopilotRunRecord) -> bool:
        inserted = connection.execute(
            """
            INSERT INTO advisory_copilot_runs (
                run_id, schema_version, action_family, audience, portfolio_id, proposal_id,
                evidence_packet_id, evidence_packet_hash, request_hash, output_hash,
                review_posture, client_ready_publication, retention_class, legal_hold,
                retention_expires_at, created_by, caller_app, tenant_id, admitted_tenant_id,
                correlation_id,
                idempotency_key, created_at, updated_at, lotus_ai_workflow_run_id,
                lotus_ai_model_version, workflow_pack_id, workflow_pack_version,
                prompt_template_version, output_schema_version, evaluation_pack_ref,
                evidence_packet_json, request_summary_json, output_sections_json,
                review_guidance_json, guardrail_results_json, lineage_json
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT DO NOTHING
            RETURNING run_id
            """,
            run_values(run)[:18] + (run.tenant_id,) + run_values(run)[18:],
        ).fetchone()
        return inserted is not None

    def _find_idempotent_run(
        self,
        *,
        connection: Any,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord | None:
        if idempotency is None:
            return None
        existing = self._find_idempotency_record(connection=connection, idempotency=idempotency)
        if existing is None or existing["request_hash"] != idempotency.request_hash:
            return None
        return self._load_admitted_idempotency_run(
            connection=connection,
            tenant_id=idempotency.tenant_id,
            run_id=existing["run_id"],
        )

    def _require_idempotent_run(
        self,
        *,
        connection: Any,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord:
        if idempotency is None:
            raise ValueError("COPILOT_RUN_NOT_FOUND")
        existing = self._find_idempotency_record(connection=connection, idempotency=idempotency)
        if existing is None:
            raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")
        if existing["request_hash"] != idempotency.request_hash:
            raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
        run = self._load_admitted_idempotency_run(
            connection=connection,
            tenant_id=idempotency.tenant_id,
            run_id=existing["run_id"],
        )
        if run is None:
            raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")
        return run

    def _require_existing_run(
        self,
        *,
        connection: Any,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord:
        if idempotency is not None:
            existing = self._find_idempotency_record(connection=connection, idempotency=idempotency)
            if existing is not None:
                return self._require_idempotent_run(connection=connection, idempotency=idempotency)
        existing_run = self._load_admitted_idempotency_run(
            connection=connection, tenant_id=run.tenant_id, run_id=run.run_id
        )
        if existing_run is None:
            raise ValueError("COPILOT_RUN_NOT_FOUND")
        if existing_run.request_hash != run.request_hash:
            raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
        if idempotency is not None:
            if not self._insert_idempotency(connection=connection, idempotency=idempotency):
                return self._require_idempotent_run(connection=connection, idempotency=idempotency)
        return existing_run

    @staticmethod
    def _find_idempotency_record(
        *,
        connection: Any,
        idempotency: AdvisoryCopilotRunIdempotencyRecord,
    ) -> Any | None:
        return connection.execute(
            """
            SELECT tenant_id, idempotency_key, request_hash, run_id, created_at
            FROM advisory_copilot_run_idempotency
            WHERE tenant_id = %s AND idempotency_key = %s
            """,
            (idempotency.tenant_id, idempotency.idempotency_key),
        ).fetchone()

    @staticmethod
    def _load_admitted_idempotency_run(
        *,
        connection: Any,
        tenant_id: str,
        run_id: str,
    ) -> AdvisoryCopilotRunRecord | None:
        row = connection.execute(
            "SELECT * FROM advisory_copilot_runs WHERE run_id = %s AND admitted_tenant_id = %s",
            (run_id, tenant_id),
        ).fetchone()
        return run_from_row(row) if row is not None else None

    def _insert_idempotency(
        self,
        *,
        connection: Any,
        idempotency: AdvisoryCopilotRunIdempotencyRecord,
    ) -> bool:
        inserted = connection.execute(
            """
            INSERT INTO advisory_copilot_run_idempotency (
                tenant_id, idempotency_key, request_hash, run_id, created_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            RETURNING run_id
            """,
            (
                idempotency.tenant_id,
                idempotency.idempotency_key,
                idempotency.request_hash,
                idempotency.run_id,
                idempotency.created_at.isoformat(),
            ),
        ).fetchone()
        return inserted is not None
