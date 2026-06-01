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
from src.infrastructure.proposals.postgres_approvals import (
    create_approval as _create_approval,
)
from src.infrastructure.proposals.postgres_approvals import (
    insert_approval as _insert_approval,
)
from src.infrastructure.proposals.postgres_approvals import (
    list_approvals as _list_approvals,
)
from src.infrastructure.proposals.postgres_approvals import (
    list_approvals_for_proposals as _list_approvals_for_proposals,
)
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
from src.infrastructure.proposals.postgres_records import (
    create_proposal as _create_proposal,
)
from src.infrastructure.proposals.postgres_records import (
    get_proposal as _get_proposal,
)
from src.infrastructure.proposals.postgres_records import (
    list_proposals as _list_proposals,
)
from src.infrastructure.proposals.postgres_records import (
    update_proposal as _update_proposal,
)
from src.infrastructure.proposals.postgres_records import (
    upsert_proposal as _upsert_proposal,
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
        _create_proposal(connect=self._connect, proposal=proposal)

    def update_proposal(self, proposal: ProposalRecord) -> None:
        _update_proposal(connect=self._connect, proposal=proposal)

    def get_proposal(self, *, proposal_id: str) -> Optional[ProposalRecord]:
        return _get_proposal(connect=self._connect, proposal_id=proposal_id)

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
        return _list_proposals(
            connect=self._connect,
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )

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
        _create_approval(connect=self._connect, approval=approval)

    def list_approvals(self, *, proposal_id: str) -> list[ProposalApprovalRecordData]:
        return cast(
            list[ProposalApprovalRecordData],
            _list_approvals(connect=self._connect, proposal_id=proposal_id),
        )

    def list_approvals_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalApprovalRecordData]:
        return cast(
            list[ProposalApprovalRecordData],
            _list_approvals_for_proposals(connect=self._connect, proposal_ids=proposal_ids),
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
                _insert_approval(connection=connection, approval=approval)
            _upsert_proposal(connection=connection, proposal=proposal)
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


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row
