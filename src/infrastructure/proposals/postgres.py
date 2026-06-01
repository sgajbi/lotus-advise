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
from src.infrastructure.proposals.postgres_cockpit_acknowledgements import (
    get_cockpit_acknowledgement as _get_cockpit_acknowledgement,
)
from src.infrastructure.proposals.postgres_cockpit_acknowledgements import (
    get_cockpit_acknowledgement_idempotency as _get_cockpit_acknowledgement_idempotency,
)
from src.infrastructure.proposals.postgres_cockpit_acknowledgements import (
    save_cockpit_acknowledgement_with_idempotency as _save_cockpit_acknowledgement_with_idempotency,
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
from src.infrastructure.proposals.postgres_memos import (
    append_memo_event as _append_memo_event,
)
from src.infrastructure.proposals.postgres_memos import (
    create_memo as _create_memo,
)
from src.infrastructure.proposals.postgres_memos import (
    get_memo as _get_memo,
)
from src.infrastructure.proposals.postgres_memos import (
    get_memo_by_proposal_version as _get_memo_by_proposal_version,
)
from src.infrastructure.proposals.postgres_memos import (
    list_memo_events as _list_memo_events,
)
from src.infrastructure.proposals.postgres_memos import (
    list_memos as _list_memos,
)
from src.infrastructure.proposals.postgres_memos import (
    list_memos_for_proposals as _list_memos_for_proposals,
)
from src.infrastructure.proposals.postgres_versions import (
    create_version as _create_version,
)
from src.infrastructure.proposals.postgres_versions import (
    get_current_version as _get_current_version,
)
from src.infrastructure.proposals.postgres_versions import (
    get_version as _get_version,
)
from src.infrastructure.proposals.postgres_versions import (
    list_versions as _list_versions,
)
from src.infrastructure.proposals.postgres_workflow_events import (
    append_event as _append_event,
)
from src.infrastructure.proposals.postgres_workflow_events import (
    insert_event as _insert_workflow_event,
)
from src.infrastructure.proposals.postgres_workflow_events import (
    list_events as _list_events,
)
from src.infrastructure.proposals.postgres_workflow_events import (
    list_events_for_proposals as _list_events_for_proposals,
)

_json_dump = _postgres_mappers.json_dump
_to_approval = _postgres_mappers.to_approval
_to_proposal = _postgres_mappers.to_proposal


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
        _create_memo(connect=self._connect, memo=memo)

    def get_memo(self, *, memo_id: str) -> Optional[ProposalMemoRecord]:
        return _get_memo(connect=self._connect, memo_id=memo_id)

    def get_memo_by_proposal_version(
        self, *, proposal_id: str, proposal_version_no: int
    ) -> Optional[ProposalMemoRecord]:
        return _get_memo_by_proposal_version(
            connect=self._connect,
            proposal_id=proposal_id,
            proposal_version_no=proposal_version_no,
        )

    def list_memos(self, *, proposal_id: str) -> list[ProposalMemoRecord]:
        return cast(
            list[ProposalMemoRecord],
            _list_memos(connect=self._connect, proposal_id=proposal_id),
        )

    def list_memos_for_proposals(self, *, proposal_ids: list[str]) -> list[ProposalMemoRecord]:
        return cast(
            list[ProposalMemoRecord],
            _list_memos_for_proposals(connect=self._connect, proposal_ids=proposal_ids),
        )

    def append_memo_event(self, event: ProposalMemoEventRecord) -> None:
        _append_memo_event(connect=self._connect, event=event)

    def list_memo_events(self, *, memo_id: str) -> list[ProposalMemoEventRecord]:
        return cast(
            list[ProposalMemoEventRecord],
            _list_memo_events(connect=self._connect, memo_id=memo_id),
        )

    def get_cockpit_acknowledgement(
        self, *, action_item_id: str
    ) -> Optional[CockpitAcknowledgementRecord]:
        return _get_cockpit_acknowledgement(
            connect=self._connect,
            action_item_id=action_item_id,
        )

    def save_cockpit_acknowledgement_with_idempotency(
        self,
        *,
        acknowledgement: CockpitAcknowledgementRecord,
        idempotency: CockpitAcknowledgementIdempotencyRecord,
    ) -> None:
        _save_cockpit_acknowledgement_with_idempotency(
            connect=self._connect,
            acknowledgement=acknowledgement,
            idempotency=idempotency,
        )

    def get_cockpit_acknowledgement_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[CockpitAcknowledgementIdempotencyRecord]:
        return _get_cockpit_acknowledgement_idempotency(
            connect=self._connect,
            idempotency_key=idempotency_key,
        )

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        _upsert_async_operation(connect=self._connect, operation=operation)

    def create_operation_if_absent_by_idempotency(
        self, operation: ProposalAsyncOperationRecord
    ) -> tuple[ProposalAsyncOperationRecord, bool]:
        return cast(
            tuple[ProposalAsyncOperationRecord, bool],
            _create_operation_if_absent_by_idempotency(
                connect=self._connect,
                operation=operation,
            ),
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
        return cast(
            list[ProposalAsyncOperationRecord],
            _list_recoverable_operations(connect=self._connect, as_of=as_of, limit=limit),
        )

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
        _create_version(connect=self._connect, version=version)

    def get_version(self, *, proposal_id: str, version_no: int) -> Optional[ProposalVersionRecord]:
        return _get_version(
            connect=self._connect,
            proposal_id=proposal_id,
            version_no=version_no,
        )

    def list_versions(self, *, proposal_id: str) -> list[ProposalVersionRecord]:
        return cast(
            list[ProposalVersionRecord],
            _list_versions(connect=self._connect, proposal_id=proposal_id),
        )

    def get_current_version(self, *, proposal_id: str) -> Optional[ProposalVersionRecord]:
        return _get_current_version(connect=self._connect, proposal_id=proposal_id)

    def append_event(self, event: ProposalWorkflowEventRecord) -> None:
        _append_event(connect=self._connect, event=event)

    def list_events(self, *, proposal_id: str) -> list[ProposalWorkflowEventRecord]:
        return cast(
            list[ProposalWorkflowEventRecord],
            _list_events(connect=self._connect, proposal_id=proposal_id),
        )

    def list_events_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalWorkflowEventRecord]:
        return cast(
            list[ProposalWorkflowEventRecord],
            _list_events_for_proposals(connect=self._connect, proposal_ids=proposal_ids),
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
            _insert_workflow_event(connection=connection, event=event)
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
