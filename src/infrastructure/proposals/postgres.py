import json
from contextlib import closing
from copy import deepcopy
from datetime import datetime
from importlib.util import find_spec
from typing import Any, Optional, cast

from src.core.advisor_cockpit.persistence import (
    CockpitAcknowledgementIdempotencyRecord,
    CockpitAcknowledgementRecord,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalIdempotencyRecord,
    ProposalMemoEventRecord,
    ProposalMemoIdempotencyRecord,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalSimulationIdempotencyRecord,
    ProposalTransitionResult,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.postgres_migrations import apply_postgres_migrations
from src.infrastructure.proposals import postgres_mappers as _postgres_mappers
from src.infrastructure.proposals.postgres_async_operations import (
    create_operation_if_absent_by_idempotency as _create_operation_if_absent_by_idempotency,
)
from src.infrastructure.proposals.postgres_async_operations import (
    get_operation as _get_operation,
)
from src.infrastructure.proposals.postgres_async_operations import (
    get_operation_by_correlation as _get_operation_by_correlation,
)
from src.infrastructure.proposals.postgres_async_operations import (
    get_operation_by_idempotency as _get_operation_by_idempotency,
)
from src.infrastructure.proposals.postgres_async_operations import (
    list_recoverable_operations as _list_recoverable_operations,
)
from src.infrastructure.proposals.postgres_async_operations import (
    upsert_operation as _upsert_async_operation,
)
from src.infrastructure.proposals.postgres_idempotency import (
    get_memo_idempotency as _get_memo_idempotency,
)
from src.infrastructure.proposals.postgres_idempotency import (
    get_proposal_idempotency as _get_proposal_idempotency,
)
from src.infrastructure.proposals.postgres_idempotency import (
    get_simulation_idempotency as _get_simulation_idempotency,
)
from src.infrastructure.proposals.postgres_idempotency import (
    save_memo_idempotency as _save_memo_idempotency,
)
from src.infrastructure.proposals.postgres_idempotency import (
    save_proposal_idempotency as _save_proposal_idempotency,
)
from src.infrastructure.proposals.postgres_idempotency import (
    save_simulation_idempotency as _save_simulation_idempotency,
)

_json_dump = _postgres_mappers.json_dump
_json_dump_list = _postgres_mappers.json_dump_list
_json_load_list = _postgres_mappers.json_load_list
_optional_datetime = _postgres_mappers.optional_datetime
_optional_iso = _postgres_mappers.optional_iso
_optional_json = _postgres_mappers.optional_json
_optional_load_json = _postgres_mappers.optional_load_json
_to_approval = _postgres_mappers.to_approval
_to_event = _postgres_mappers.to_event
_to_memo = _postgres_mappers.to_memo
_to_memo_event = _postgres_mappers.to_memo_event
_to_operation = _postgres_mappers.to_operation
_to_proposal = _postgres_mappers.to_proposal
_to_version = _postgres_mappers.to_version


class PostgresProposalRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("PROPOSAL_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def get_idempotency(self, *, idempotency_key: str) -> Optional[ProposalIdempotencyRecord]:
        return _get_proposal_idempotency(
            connect=self._connect,
            idempotency_key=idempotency_key,
        )

    def save_idempotency(self, record: ProposalIdempotencyRecord) -> None:
        _save_proposal_idempotency(connect=self._connect, record=record)

    def get_simulation_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalSimulationIdempotencyRecord]:
        return _get_simulation_idempotency(
            connect=self._connect,
            idempotency_key=idempotency_key,
        )

    def save_simulation_idempotency(self, record: ProposalSimulationIdempotencyRecord) -> None:
        _save_simulation_idempotency(connect=self._connect, record=record)

    def get_memo_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalMemoIdempotencyRecord]:
        return _get_memo_idempotency(
            connect=self._connect,
            idempotency_key=idempotency_key,
        )

    def save_memo_idempotency(self, record: ProposalMemoIdempotencyRecord) -> None:
        _save_memo_idempotency(connect=self._connect, record=record)

    def create_memo(self, memo: ProposalMemoRecord) -> None:
        query = """
            INSERT INTO proposal_memos (
                memo_id,
                proposal_id,
                proposal_version_no,
                proposal_version_id,
                artifact_id,
                memo_version,
                memo_status,
                lifecycle_status,
                created_by,
                created_at,
                source_input_hash,
                memo_hash,
                memo_json,
                projection_json,
                review_events_json,
                report_package_events_json,
                archive_refs_json,
                ai_refs_json,
                replay_metadata_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    memo.memo_id,
                    memo.proposal_id,
                    memo.proposal_version_no,
                    memo.proposal_version_id,
                    memo.artifact_id,
                    memo.memo_version,
                    memo.memo_status,
                    memo.lifecycle_status,
                    memo.created_by,
                    memo.created_at.isoformat(),
                    memo.source_input_hash,
                    memo.memo_hash,
                    _json_dump(memo.memo_json),
                    _json_dump(memo.projection_json),
                    _json_dump_list(memo.review_events_json),
                    _json_dump_list(memo.report_package_events_json),
                    _json_dump_list(memo.archive_refs_json),
                    _json_dump_list(memo.ai_refs_json),
                    _json_dump(memo.replay_metadata_json),
                ),
            )
            connection.commit()

    def get_memo(self, *, memo_id: str) -> Optional[ProposalMemoRecord]:
        query = """
            SELECT
                memo_id,
                proposal_id,
                proposal_version_no,
                proposal_version_id,
                artifact_id,
                memo_version,
                memo_status,
                lifecycle_status,
                created_by,
                created_at,
                source_input_hash,
                memo_hash,
                memo_json,
                projection_json,
                review_events_json,
                report_package_events_json,
                archive_refs_json,
                ai_refs_json,
                replay_metadata_json
            FROM proposal_memos
            WHERE memo_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (memo_id,)).fetchone()
        return _to_memo(row)

    def get_memo_by_proposal_version(
        self, *, proposal_id: str, proposal_version_no: int
    ) -> Optional[ProposalMemoRecord]:
        query = """
            SELECT
                memo_id,
                proposal_id,
                proposal_version_no,
                proposal_version_id,
                artifact_id,
                memo_version,
                memo_status,
                lifecycle_status,
                created_by,
                created_at,
                source_input_hash,
                memo_hash,
                memo_json,
                projection_json,
                review_events_json,
                report_package_events_json,
                archive_refs_json,
                ai_refs_json,
                replay_metadata_json
            FROM proposal_memos
            WHERE proposal_id = %s AND proposal_version_no = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (proposal_id, proposal_version_no)).fetchone()
        return _to_memo(row)

    def list_memos(self, *, proposal_id: str) -> list[ProposalMemoRecord]:
        query = """
            SELECT
                memo_id,
                proposal_id,
                proposal_version_no,
                proposal_version_id,
                artifact_id,
                memo_version,
                memo_status,
                lifecycle_status,
                created_by,
                created_at,
                source_input_hash,
                memo_hash,
                memo_json,
                projection_json,
                review_events_json,
                report_package_events_json,
                archive_refs_json,
                ai_refs_json,
                replay_metadata_json
            FROM proposal_memos
            WHERE proposal_id = %s
            ORDER BY proposal_version_no ASC, created_at ASC, memo_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_id,)).fetchall()
        return [memo for row in rows if (memo := _to_memo(row)) is not None]

    def list_memos_for_proposals(self, *, proposal_ids: list[str]) -> list[ProposalMemoRecord]:
        if not proposal_ids:
            return []
        query = """
            SELECT
                memo_id,
                proposal_id,
                proposal_version_no,
                proposal_version_id,
                artifact_id,
                memo_version,
                memo_status,
                lifecycle_status,
                created_by,
                created_at,
                source_input_hash,
                memo_hash,
                memo_json,
                projection_json,
                review_events_json,
                report_package_events_json,
                archive_refs_json,
                ai_refs_json,
                replay_metadata_json
            FROM proposal_memos
            WHERE proposal_id = ANY(%s)
            ORDER BY proposal_id ASC, proposal_version_no ASC, created_at ASC, memo_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_ids,)).fetchall()
        memo_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
        memos = [memo for row in rows if (memo := _to_memo(row)) is not None]
        return sorted(
            memos,
            key=lambda memo: (
                memo_order.get(memo.proposal_id, len(memo_order)),
                memo.proposal_version_no,
                memo.created_at,
                memo.memo_id,
            ),
        )

    def append_memo_event(self, event: ProposalMemoEventRecord) -> None:
        query = """
            INSERT INTO proposal_memo_events (
                event_id,
                memo_id,
                proposal_id,
                proposal_version_no,
                event_type,
                actor_id,
                occurred_at,
                reason_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    event.event_id,
                    event.memo_id,
                    event.proposal_id,
                    event.proposal_version_no,
                    event.event_type,
                    event.actor_id,
                    event.occurred_at.isoformat(),
                    _json_dump(event.reason_json),
                ),
            )
            connection.commit()

    def list_memo_events(self, *, memo_id: str) -> list[ProposalMemoEventRecord]:
        query = """
            SELECT
                event_id,
                memo_id,
                proposal_id,
                proposal_version_no,
                event_type,
                actor_id,
                occurred_at,
                reason_json
            FROM proposal_memo_events
            WHERE memo_id = %s
            ORDER BY occurred_at ASC, event_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (memo_id,)).fetchall()
        return [_to_memo_event(row) for row in rows]

    def get_cockpit_acknowledgement(
        self, *, action_item_id: str
    ) -> Optional[CockpitAcknowledgementRecord]:
        query = """
            SELECT
                acknowledgement_id,
                action_item_id,
                action_item_version,
                acknowledged_by,
                acknowledged_at,
                acknowledgement_note,
                correlation_id,
                reason_json
            FROM advisor_cockpit_acknowledgements
            WHERE action_item_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (action_item_id,)).fetchone()
        if row is None:
            return None
        return CockpitAcknowledgementRecord(
            acknowledgement_id=row["acknowledgement_id"],
            action_item_id=row["action_item_id"],
            action_item_version=int(row["action_item_version"]),
            acknowledged_by=row["acknowledged_by"],
            acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]),
            acknowledgement_note=row["acknowledgement_note"],
            correlation_id=row["correlation_id"],
            reason_json=json.loads(row["reason_json"]),
        )

    def save_cockpit_acknowledgement_with_idempotency(
        self,
        *,
        acknowledgement: CockpitAcknowledgementRecord,
        idempotency: CockpitAcknowledgementIdempotencyRecord,
    ) -> None:
        idempotency_query = """
            INSERT INTO advisor_cockpit_acknowledgement_idempotency (
                idempotency_key,
                request_hash,
                acknowledgement_id,
                action_item_id,
                created_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
        """
        idempotency_lookup = """
            SELECT
                idempotency_key,
                request_hash,
                acknowledgement_id,
                action_item_id,
                created_at
            FROM advisor_cockpit_acknowledgement_idempotency
            WHERE idempotency_key = %s
        """
        acknowledgement_query = """
            INSERT INTO advisor_cockpit_acknowledgements (
                acknowledgement_id,
                action_item_id,
                action_item_version,
                acknowledged_by,
                acknowledged_at,
                acknowledgement_note,
                correlation_id,
                reason_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (action_item_id) DO UPDATE SET
                action_item_version=excluded.action_item_version,
                acknowledged_by=excluded.acknowledged_by,
                acknowledged_at=excluded.acknowledged_at,
                acknowledgement_note=excluded.acknowledgement_note,
                correlation_id=excluded.correlation_id,
                reason_json=excluded.reason_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                idempotency_query,
                (
                    idempotency.idempotency_key,
                    idempotency.request_hash,
                    idempotency.acknowledgement_id,
                    idempotency.action_item_id,
                    idempotency.created_at.isoformat(),
                ),
            )
            existing = connection.execute(
                idempotency_lookup, (idempotency.idempotency_key,)
            ).fetchone()
            if existing is None:
                connection.rollback()
                raise RuntimeError("COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_WRITE_FAILED")
            if (
                existing["request_hash"] != idempotency.request_hash
                or existing["acknowledgement_id"] != idempotency.acknowledgement_id
                or existing["action_item_id"] != idempotency.action_item_id
            ):
                connection.rollback()
                raise ValueError("COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_KEY_CONFLICT")
            connection.execute(
                acknowledgement_query,
                (
                    acknowledgement.acknowledgement_id,
                    acknowledgement.action_item_id,
                    acknowledgement.action_item_version,
                    acknowledgement.acknowledged_by,
                    acknowledgement.acknowledged_at.isoformat(),
                    acknowledgement.acknowledgement_note,
                    acknowledgement.correlation_id,
                    _json_dump(acknowledgement.reason_json),
                ),
            )
            connection.commit()

    def get_cockpit_acknowledgement_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[CockpitAcknowledgementIdempotencyRecord]:
        query = """
            SELECT
                idempotency_key,
                request_hash,
                acknowledgement_id,
                action_item_id,
                created_at
            FROM advisor_cockpit_acknowledgement_idempotency
            WHERE idempotency_key = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (idempotency_key,)).fetchone()
        if row is None:
            return None
        return CockpitAcknowledgementIdempotencyRecord(
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            acknowledgement_id=row["acknowledgement_id"],
            action_item_id=row["action_item_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        _upsert_async_operation(connect=self._connect, operation=operation)

    def create_operation_if_absent_by_idempotency(
        self, operation: ProposalAsyncOperationRecord
    ) -> tuple[ProposalAsyncOperationRecord, bool]:
        return _create_operation_if_absent_by_idempotency(
            connect=self._connect,
            operation=operation,
        )

    def update_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        _upsert_async_operation(connect=self._connect, operation=operation)

    def get_operation(self, *, operation_id: str) -> Optional[ProposalAsyncOperationRecord]:
        return _get_operation(connect=self._connect, operation_id=operation_id)

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        return _get_operation_by_correlation(connect=self._connect, correlation_id=correlation_id)

    def get_operation_by_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        return _get_operation_by_idempotency(connect=self._connect, idempotency_key=idempotency_key)

    def list_recoverable_operations(
        self, *, as_of: datetime, limit: Optional[int] = None
    ) -> list[ProposalAsyncOperationRecord]:
        return _list_recoverable_operations(connect=self._connect, as_of=as_of, limit=limit)

    def create_proposal(self, proposal: ProposalRecord) -> None:
        with closing(self._connect()) as connection:
            self._upsert_proposal(connection=connection, proposal=proposal)
            connection.commit()

    def update_proposal(self, proposal: ProposalRecord) -> None:
        with closing(self._connect()) as connection:
            self._upsert_proposal(connection=connection, proposal=proposal)
            connection.commit()

    def get_proposal(self, *, proposal_id: str) -> Optional[ProposalRecord]:
        query = """
            SELECT
                proposal_id,
                portfolio_id,
                mandate_id,
                jurisdiction,
                created_by,
                created_at,
                last_event_at,
                current_state,
                current_version_no,
                title,
                advisor_notes,
                lifecycle_origin,
                source_workspace_id
            FROM proposal_records
            WHERE proposal_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (proposal_id,)).fetchone()
        return _to_proposal(row)

    def list_proposals(
        self,
        *,
        portfolio_id: Optional[str],
        state: Optional[str],
        created_by: Optional[str],
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[ProposalRecord], Optional[str]]:
        where_clauses = []
        args: list[object] = []
        cursor_where_clauses = ["cursor_record.proposal_id = %s"]
        cursor_args: list[object] = []

        def add_filter(clause: str, cursor_clause: str, value: object) -> None:
            where_clauses.append(clause)
            args.append(value)
            cursor_where_clauses.append(cursor_clause)
            cursor_args.append(value)

        if portfolio_id is not None:
            add_filter("portfolio_id = %s", "cursor_record.portfolio_id = %s", portfolio_id)
        if state is not None:
            add_filter("current_state = %s", "cursor_record.current_state = %s", state)
        if created_by is not None:
            add_filter("created_by = %s", "cursor_record.created_by = %s", created_by)
        if created_from is not None:
            add_filter(
                "created_at >= %s",
                "cursor_record.created_at >= %s",
                created_from.isoformat(),
            )
        if created_to is not None:
            add_filter(
                "created_at <= %s",
                "cursor_record.created_at <= %s",
                created_to.isoformat(),
            )
        if cursor:
            cursor_args.insert(0, cursor)
            cursor_where_sql = " AND ".join(cursor_where_clauses)
            where_clauses.append(
                f"""
                (created_at, proposal_id) < (
                    SELECT cursor_record.created_at, cursor_record.proposal_id
                    FROM proposal_records cursor_record
                    WHERE {cursor_where_sql}
                )
                """
            )
            args.extend(cursor_args)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT
                proposal_id,
                portfolio_id,
                mandate_id,
                jurisdiction,
                created_by,
                created_at,
                last_event_at,
                current_state,
                current_version_no,
                title,
                advisor_notes,
                lifecycle_origin,
                source_workspace_id
            FROM proposal_records
            {where_sql}
            ORDER BY created_at DESC, proposal_id DESC
            LIMIT %s
        """
        args.append(limit + 1)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        proposals = cast(
            list[ProposalRecord],
            [proposal for proposal in (_to_proposal(row) for row in rows) if proposal is not None],
        )
        page = proposals[:limit]
        next_cursor = page[-1].proposal_id if len(proposals) > limit else None
        return page, next_cursor

    def create_version(self, version: ProposalVersionRecord) -> None:
        query = """
            INSERT INTO proposal_versions (
                proposal_version_id,
                proposal_id,
                version_no,
                created_at,
                request_hash,
                artifact_hash,
                simulation_hash,
                status_at_creation,
                proposal_result_json,
                artifact_json,
                evidence_bundle_json,
                gate_decision_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (proposal_id, version_no) DO UPDATE SET
                proposal_version_id=excluded.proposal_version_id,
                created_at=excluded.created_at,
                request_hash=excluded.request_hash,
                artifact_hash=excluded.artifact_hash,
                simulation_hash=excluded.simulation_hash,
                status_at_creation=excluded.status_at_creation,
                proposal_result_json=excluded.proposal_result_json,
                artifact_json=excluded.artifact_json,
                evidence_bundle_json=excluded.evidence_bundle_json,
                gate_decision_json=excluded.gate_decision_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    version.proposal_version_id,
                    version.proposal_id,
                    version.version_no,
                    version.created_at.isoformat(),
                    version.request_hash,
                    version.artifact_hash,
                    version.simulation_hash,
                    version.status_at_creation,
                    _json_dump(version.proposal_result_json),
                    _json_dump(version.artifact_json),
                    _json_dump(version.evidence_bundle_json),
                    _optional_json(version.gate_decision_json),
                ),
            )
            connection.commit()

    def get_version(self, *, proposal_id: str, version_no: int) -> Optional[ProposalVersionRecord]:
        query = """
            SELECT
                proposal_version_id,
                proposal_id,
                version_no,
                created_at,
                request_hash,
                artifact_hash,
                simulation_hash,
                status_at_creation,
                proposal_result_json,
                artifact_json,
                evidence_bundle_json,
                gate_decision_json
            FROM proposal_versions
            WHERE proposal_id = %s AND version_no = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (proposal_id, version_no)).fetchone()
        return _to_version(row)

    def list_versions(self, *, proposal_id: str) -> list[ProposalVersionRecord]:
        query = """
            SELECT
                proposal_version_id,
                proposal_id,
                version_no,
                created_at,
                request_hash,
                artifact_hash,
                simulation_hash,
                status_at_creation,
                proposal_result_json,
                artifact_json,
                evidence_bundle_json,
                gate_decision_json
            FROM proposal_versions
            WHERE proposal_id = %s
            ORDER BY version_no ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_id,)).fetchall()
        return [version for row in rows if (version := _to_version(row)) is not None]

    def get_current_version(self, *, proposal_id: str) -> Optional[ProposalVersionRecord]:
        query = """
            SELECT
                proposal_version_id,
                proposal_id,
                version_no,
                created_at,
                request_hash,
                artifact_hash,
                simulation_hash,
                status_at_creation,
                proposal_result_json,
                artifact_json,
                evidence_bundle_json,
                gate_decision_json
            FROM proposal_versions
            WHERE proposal_id = %s
            ORDER BY version_no DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (proposal_id,)).fetchone()
        return _to_version(row)

    def append_event(self, event: ProposalWorkflowEventRecord) -> None:
        with closing(self._connect()) as connection:
            self._insert_event(connection=connection, event=event)
            connection.commit()

    def list_events(self, *, proposal_id: str) -> list[ProposalWorkflowEventRecord]:
        query = """
            SELECT
                event_id,
                proposal_id,
                event_type,
                from_state,
                to_state,
                actor_id,
                occurred_at,
                reason_json,
                related_version_no
            FROM proposal_workflow_events
            WHERE proposal_id = %s
            ORDER BY occurred_at ASC, event_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_id,)).fetchall()
        return [_to_event(row) for row in rows]

    def list_events_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalWorkflowEventRecord]:
        if not proposal_ids:
            return []
        query = """
            SELECT
                event_id,
                proposal_id,
                event_type,
                from_state,
                to_state,
                actor_id,
                occurred_at,
                reason_json,
                related_version_no
            FROM proposal_workflow_events
            WHERE proposal_id = ANY(%s)
            ORDER BY proposal_id ASC, occurred_at ASC, event_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_ids,)).fetchall()
        event_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
        events = [_to_event(row) for row in rows]
        return sorted(
            events,
            key=lambda event: (
                event_order.get(event.proposal_id, len(event_order)),
                event.occurred_at,
                event.event_id,
            ),
        )

    def create_approval(self, approval: ProposalApprovalRecordData) -> None:
        with closing(self._connect()) as connection:
            self._insert_approval(connection=connection, approval=approval)
            connection.commit()

    def list_approvals(self, *, proposal_id: str) -> list[ProposalApprovalRecordData]:
        query = """
            SELECT
                approval_id,
                proposal_id,
                approval_type,
                approved,
                actor_id,
                occurred_at,
                details_json,
                related_version_no
            FROM proposal_approvals
            WHERE proposal_id = %s
            ORDER BY occurred_at ASC, approval_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_id,)).fetchall()
        return [_to_approval(row) for row in rows]

    def list_approvals_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalApprovalRecordData]:
        if not proposal_ids:
            return []
        query = """
            SELECT
                approval_id,
                proposal_id,
                approval_type,
                approved,
                actor_id,
                occurred_at,
                details_json,
                related_version_no
            FROM proposal_approvals
            WHERE proposal_id = ANY(%s)
            ORDER BY proposal_id ASC, occurred_at ASC, approval_id ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (proposal_ids,)).fetchall()
        approval_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
        approvals = [_to_approval(row) for row in rows]
        return sorted(
            approvals,
            key=lambda approval: (
                approval_order.get(approval.proposal_id, len(approval_order)),
                approval.occurred_at,
                approval.approval_id,
            ),
        )

    def transition_proposal(
        self,
        *,
        proposal: ProposalRecord,
        event: ProposalWorkflowEventRecord,
        approval: Optional[ProposalApprovalRecordData],
    ) -> ProposalTransitionResult:
        with closing(self._connect()) as connection:
            self._insert_event(connection=connection, event=event)
            if approval is not None:
                self._insert_approval(connection=connection, approval=approval)
            self._upsert_proposal(connection=connection, proposal=proposal)
            connection.commit()

        return ProposalTransitionResult(
            proposal=deepcopy(proposal),
            event=deepcopy(event),
            approval=deepcopy(approval) if approval is not None else None,
        )

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="proposals")

    def _upsert_proposal(self, *, connection: Any, proposal: ProposalRecord) -> None:
        query = """
            INSERT INTO proposal_records (
                proposal_id,
                portfolio_id,
                mandate_id,
                jurisdiction,
                created_by,
                created_at,
                last_event_at,
                current_state,
                current_version_no,
                title,
                advisor_notes,
                lifecycle_origin,
                source_workspace_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (proposal_id) DO UPDATE SET
                portfolio_id=excluded.portfolio_id,
                mandate_id=excluded.mandate_id,
                jurisdiction=excluded.jurisdiction,
                created_by=excluded.created_by,
                created_at=excluded.created_at,
                last_event_at=excluded.last_event_at,
                current_state=excluded.current_state,
                current_version_no=excluded.current_version_no,
                title=excluded.title,
                advisor_notes=excluded.advisor_notes,
                lifecycle_origin=excluded.lifecycle_origin,
                source_workspace_id=excluded.source_workspace_id
        """
        connection.execute(
            query,
            (
                proposal.proposal_id,
                proposal.portfolio_id,
                proposal.mandate_id,
                proposal.jurisdiction,
                proposal.created_by,
                proposal.created_at.isoformat(),
                proposal.last_event_at.isoformat(),
                proposal.current_state,
                proposal.current_version_no,
                proposal.title,
                proposal.advisor_notes,
                proposal.lifecycle_origin,
                proposal.source_workspace_id,
            ),
        )

    def _insert_event(self, *, connection: Any, event: ProposalWorkflowEventRecord) -> None:
        query = """
            INSERT INTO proposal_workflow_events (
                event_id,
                proposal_id,
                event_type,
                from_state,
                to_state,
                actor_id,
                occurred_at,
                reason_json,
                related_version_no
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO UPDATE SET
                proposal_id=excluded.proposal_id,
                event_type=excluded.event_type,
                from_state=excluded.from_state,
                to_state=excluded.to_state,
                actor_id=excluded.actor_id,
                occurred_at=excluded.occurred_at,
                reason_json=excluded.reason_json,
                related_version_no=excluded.related_version_no
        """
        connection.execute(
            query,
            (
                event.event_id,
                event.proposal_id,
                event.event_type,
                event.from_state,
                event.to_state,
                event.actor_id,
                event.occurred_at.isoformat(),
                _json_dump(event.reason_json),
                event.related_version_no,
            ),
        )

    def _insert_approval(self, *, connection: Any, approval: ProposalApprovalRecordData) -> None:
        query = """
            INSERT INTO proposal_approvals (
                approval_id,
                proposal_id,
                approval_type,
                approved,
                actor_id,
                occurred_at,
                details_json,
                related_version_no
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (approval_id) DO UPDATE SET
                proposal_id=excluded.proposal_id,
                approval_type=excluded.approval_type,
                approved=excluded.approved,
                actor_id=excluded.actor_id,
                occurred_at=excluded.occurred_at,
                details_json=excluded.details_json,
                related_version_no=excluded.related_version_no
        """
        connection.execute(
            query,
            (
                approval.approval_id,
                approval.proposal_id,
                approval.approval_type,
                approval.approved,
                approval.actor_id,
                approval.occurred_at.isoformat(),
                _json_dump(approval.details_json),
                approval.related_version_no,
            ),
        )


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row
