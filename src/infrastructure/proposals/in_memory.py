from copy import deepcopy
from datetime import datetime
from threading import Lock
from typing import Optional

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
from src.core.proposals.repository import ProposalRepository


class InMemoryProposalRepository(ProposalRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._proposals: dict[str, ProposalRecord] = {}
        self._versions: dict[tuple[str, int], ProposalVersionRecord] = {}
        self._events: dict[str, list[ProposalWorkflowEventRecord]] = {}
        self._approvals: dict[str, list[ProposalApprovalRecordData]] = {}
        self._idempotency: dict[str, ProposalIdempotencyRecord] = {}
        self._simulation_idempotency: dict[str, ProposalSimulationIdempotencyRecord] = {}
        self._memo_idempotency: dict[str, ProposalMemoIdempotencyRecord] = {}
        self._operations: dict[str, ProposalAsyncOperationRecord] = {}
        self._operation_by_correlation: dict[str, str] = {}
        self._operation_by_idempotency: dict[str, str] = {}
        self._memos: dict[str, ProposalMemoRecord] = {}
        self._memo_by_proposal_version: dict[tuple[str, int], str] = {}
        self._memo_events: dict[str, list[ProposalMemoEventRecord]] = {}
        self._cockpit_acknowledgements: dict[str, CockpitAcknowledgementRecord] = {}
        self._cockpit_acknowledgement_idempotency: dict[
            str, CockpitAcknowledgementIdempotencyRecord
        ] = {}

    def get_idempotency(self, *, idempotency_key: str) -> Optional[ProposalIdempotencyRecord]:
        with self._lock:
            record = self._idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def save_idempotency(self, record: ProposalIdempotencyRecord) -> None:
        with self._lock:
            self._idempotency[record.idempotency_key] = deepcopy(record)

    def get_simulation_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalSimulationIdempotencyRecord]:
        with self._lock:
            record = self._simulation_idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def save_simulation_idempotency(self, record: ProposalSimulationIdempotencyRecord) -> None:
        with self._lock:
            self._simulation_idempotency[record.idempotency_key] = deepcopy(record)

    def get_memo_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalMemoIdempotencyRecord]:
        with self._lock:
            record = self._memo_idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def save_memo_idempotency(self, record: ProposalMemoIdempotencyRecord) -> None:
        with self._lock:
            existing = self._memo_idempotency.get(record.idempotency_key)
            if existing is not None:
                request_changed = existing.request_hash != record.request_hash
                memo_changed = existing.memo_id != record.memo_id
                if request_changed or memo_changed:
                    raise ValueError("MEMO_IDEMPOTENCY_KEY_CONFLICT")
                return
            self._memo_idempotency[record.idempotency_key] = deepcopy(record)

    def create_memo(self, memo: ProposalMemoRecord) -> None:
        with self._lock:
            proposal_version_key = (memo.proposal_id, memo.proposal_version_no)
            existing_memo_id = self._memo_by_proposal_version.get(proposal_version_key)
            if existing_memo_id is not None and existing_memo_id != memo.memo_id:
                raise ValueError("MEMO_PROPOSAL_VERSION_CONFLICT")
            if memo.memo_id in self._memos:
                existing = self._memos[memo.memo_id]
                if existing.memo_hash != memo.memo_hash:
                    raise ValueError("MEMO_HASH_CONFLICT")
                return
            self._memos[memo.memo_id] = deepcopy(memo)
            self._memo_by_proposal_version[proposal_version_key] = memo.memo_id

    def get_memo(self, *, memo_id: str) -> Optional[ProposalMemoRecord]:
        with self._lock:
            memo = self._memos.get(memo_id)
            return deepcopy(memo) if memo is not None else None

    def get_memo_by_proposal_version(
        self, *, proposal_id: str, proposal_version_no: int
    ) -> Optional[ProposalMemoRecord]:
        with self._lock:
            memo_id = self._memo_by_proposal_version.get((proposal_id, proposal_version_no))
            if memo_id is None:
                return None
            memo = self._memos.get(memo_id)
            return deepcopy(memo) if memo is not None else None

    def list_memos(self, *, proposal_id: str) -> list[ProposalMemoRecord]:
        with self._lock:
            memos = [memo for memo in self._memos.values() if memo.proposal_id == proposal_id]
        memos.sort(key=lambda memo: (memo.proposal_version_no, memo.created_at, memo.memo_id))
        return [deepcopy(memo) for memo in memos]

    def list_memos_for_proposals(self, *, proposal_ids: list[str]) -> list[ProposalMemoRecord]:
        if not proposal_ids:
            return []
        proposal_id_set = set(proposal_ids)
        memo_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
        with self._lock:
            memos = [memo for memo in self._memos.values() if memo.proposal_id in proposal_id_set]
        memos.sort(
            key=lambda memo: (
                memo_order[memo.proposal_id],
                memo.proposal_version_no,
                memo.created_at,
                memo.memo_id,
            )
        )
        return [deepcopy(memo) for memo in memos]

    def append_memo_event(self, event: ProposalMemoEventRecord) -> None:
        with self._lock:
            events = self._memo_events.setdefault(event.memo_id, [])
            if any(existing.event_id == event.event_id for existing in events):
                return
            events.append(deepcopy(event))

    def list_memo_events(self, *, memo_id: str) -> list[ProposalMemoEventRecord]:
        with self._lock:
            events = self._memo_events.get(memo_id, [])
        events = sorted(events, key=lambda event: (event.occurred_at, event.event_id))
        return [deepcopy(event) for event in events]

    def get_cockpit_acknowledgement(
        self, *, action_item_id: str
    ) -> Optional[CockpitAcknowledgementRecord]:
        with self._lock:
            record = self._cockpit_acknowledgements.get(action_item_id)
            return deepcopy(record) if record is not None else None

    def save_cockpit_acknowledgement_with_idempotency(
        self,
        *,
        acknowledgement: CockpitAcknowledgementRecord,
        idempotency: CockpitAcknowledgementIdempotencyRecord,
    ) -> None:
        with self._lock:
            existing = self._cockpit_acknowledgement_idempotency.get(idempotency.idempotency_key)
            if existing is not None:
                if (
                    existing.request_hash != idempotency.request_hash
                    or existing.acknowledgement_id != idempotency.acknowledgement_id
                    or existing.action_item_id != idempotency.action_item_id
                ):
                    raise ValueError("COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_KEY_CONFLICT")
                return
            self._cockpit_acknowledgement_idempotency[idempotency.idempotency_key] = deepcopy(
                idempotency
            )
            self._cockpit_acknowledgements[acknowledgement.action_item_id] = deepcopy(
                acknowledgement
            )

    def get_cockpit_acknowledgement_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[CockpitAcknowledgementIdempotencyRecord]:
        with self._lock:
            record = self._cockpit_acknowledgement_idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        with self._lock:
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id
            if operation.idempotency_key:
                self._operation_by_idempotency[operation.idempotency_key] = operation.operation_id

    def create_operation_if_absent_by_idempotency(
        self, operation: ProposalAsyncOperationRecord
    ) -> tuple[ProposalAsyncOperationRecord, bool]:
        with self._lock:
            if operation.idempotency_key:
                existing_operation_id = self._operation_by_idempotency.get(
                    operation.idempotency_key
                )
                if existing_operation_id is not None:
                    existing = self._operations.get(existing_operation_id)
                    if existing is not None:
                        return deepcopy(existing), False
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id
            if operation.idempotency_key:
                self._operation_by_idempotency[operation.idempotency_key] = operation.operation_id
            return deepcopy(operation), True

    def update_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        with self._lock:
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id
            if operation.idempotency_key:
                self._operation_by_idempotency[operation.idempotency_key] = operation.operation_id

    def get_operation(self, *, operation_id: str) -> Optional[ProposalAsyncOperationRecord]:
        with self._lock:
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        with self._lock:
            operation_id = self._operation_by_correlation.get(correlation_id)
            if operation_id is None:
                return None
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_by_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        with self._lock:
            operation_id = self._operation_by_idempotency.get(idempotency_key)
            if operation_id is None:
                return None
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def list_recoverable_operations(
        self, *, as_of: datetime, limit: Optional[int] = None
    ) -> list[ProposalAsyncOperationRecord]:
        if limit is not None and limit <= 0:
            return []
        with self._lock:
            operations = list(self._operations.values())
        recoverable = [
            operation
            for operation in operations
            if operation.status == "PENDING"
            or (
                operation.status == "RUNNING"
                and operation.finished_at is None
                and operation.lease_expires_at is not None
                and operation.lease_expires_at <= as_of
            )
        ]
        recoverable.sort(key=lambda operation: (operation.created_at, operation.operation_id))
        if limit is not None:
            recoverable = recoverable[:limit]
        return [deepcopy(operation) for operation in recoverable]

    def create_proposal(self, proposal: ProposalRecord) -> None:
        with self._lock:
            self._proposals[proposal.proposal_id] = deepcopy(proposal)

    def update_proposal(self, proposal: ProposalRecord) -> None:
        with self._lock:
            self._proposals[proposal.proposal_id] = deepcopy(proposal)

    def get_proposal(self, *, proposal_id: str) -> Optional[ProposalRecord]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            return deepcopy(proposal) if proposal is not None else None

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
        with self._lock:
            rows = list(self._proposals.values())

        rows = sorted(rows, key=lambda x: (x.created_at, x.proposal_id), reverse=True)

        if portfolio_id is not None:
            rows = [row for row in rows if row.portfolio_id == portfolio_id]
        if state is not None:
            rows = [row for row in rows if row.current_state == state]
        if created_by is not None:
            rows = [row for row in rows if row.created_by == created_by]
        if created_from is not None:
            rows = [row for row in rows if row.created_at >= created_from]
        if created_to is not None:
            rows = [row for row in rows if row.created_at <= created_to]

        if cursor:
            row_ids = [row.proposal_id for row in rows]
            if cursor in row_ids:
                start = row_ids.index(cursor) + 1
                rows = rows[start:]

        page = rows[:limit]
        next_cursor = page[-1].proposal_id if len(rows) > limit else None
        return [deepcopy(row) for row in page], next_cursor

    def create_version(self, version: ProposalVersionRecord) -> None:
        with self._lock:
            self._versions[(version.proposal_id, version.version_no)] = deepcopy(version)

    def get_version(self, *, proposal_id: str, version_no: int) -> Optional[ProposalVersionRecord]:
        with self._lock:
            version = self._versions.get((proposal_id, version_no))
            return deepcopy(version) if version is not None else None

    def list_versions(self, *, proposal_id: str) -> list[ProposalVersionRecord]:
        with self._lock:
            versions = [
                version
                for (stored_proposal_id, _), version in self._versions.items()
                if stored_proposal_id == proposal_id
            ]
        versions.sort(key=lambda version: version.version_no)
        return [deepcopy(version) for version in versions]

    def get_current_version(self, *, proposal_id: str) -> Optional[ProposalVersionRecord]:
        with self._lock:
            versions = [v for (pid, _), v in self._versions.items() if pid == proposal_id]
        if not versions:
            return None
        versions.sort(key=lambda x: x.version_no, reverse=True)
        return deepcopy(versions[0])

    def append_event(self, event: ProposalWorkflowEventRecord) -> None:
        with self._lock:
            events = self._events.setdefault(event.proposal_id, [])
            events.append(deepcopy(event))

    def list_events(self, *, proposal_id: str) -> list[ProposalWorkflowEventRecord]:
        with self._lock:
            events = self._events.get(proposal_id, [])
            return [deepcopy(event) for event in events]

    def create_approval(self, approval: ProposalApprovalRecordData) -> None:
        with self._lock:
            approvals = self._approvals.setdefault(approval.proposal_id, [])
            approvals.append(deepcopy(approval))

    def list_approvals(self, *, proposal_id: str) -> list[ProposalApprovalRecordData]:
        with self._lock:
            approvals = self._approvals.get(proposal_id, [])
            return [deepcopy(approval) for approval in approvals]

    def list_approvals_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalApprovalRecordData]:
        if not proposal_ids:
            return []
        proposal_id_set = set(proposal_ids)
        approval_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
        with self._lock:
            approvals = [
                approval
                for proposal_approvals in self._approvals.values()
                for approval in proposal_approvals
                if approval.proposal_id in proposal_id_set
            ]
        approvals.sort(
            key=lambda approval: (
                approval_order[approval.proposal_id],
                approval.occurred_at,
                approval.approval_id,
            )
        )
        return [deepcopy(approval) for approval in approvals]

    def transition_proposal(
        self,
        *,
        proposal: ProposalRecord,
        event: ProposalWorkflowEventRecord,
        approval: Optional[ProposalApprovalRecordData],
    ) -> ProposalTransitionResult:
        with self._lock:
            self._events.setdefault(event.proposal_id, []).append(deepcopy(event))
            if approval is not None:
                self._approvals.setdefault(approval.proposal_id, []).append(deepcopy(approval))
            self._proposals[proposal.proposal_id] = deepcopy(proposal)

        return ProposalTransitionResult(
            proposal=deepcopy(proposal),
            event=deepcopy(event),
            approval=deepcopy(approval) if approval is not None else None,
        )
