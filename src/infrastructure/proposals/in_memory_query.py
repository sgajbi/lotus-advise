from copy import deepcopy
from datetime import datetime
from typing import Iterable, Optional, TypeVar, cast

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalMemoEventRecord,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)

RecordT = TypeVar("RecordT")


def copy_optional(record: RecordT | None) -> RecordT | None:
    return deepcopy(record) if record is not None else None


def copy_record(record: RecordT) -> RecordT:
    return deepcopy(record)


def copy_records(records: Iterable[RecordT]) -> list[RecordT]:
    return [deepcopy(record) for record in records]


def filtered_proposal_page(
    rows: Iterable[ProposalRecord],
    *,
    portfolio_id: Optional[str],
    state: Optional[str],
    created_by: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    limit: int,
    cursor: Optional[str],
) -> tuple[list[ProposalRecord], Optional[str]]:
    filtered = sorted(rows, key=lambda row: (row.created_at, row.proposal_id), reverse=True)
    filtered = [
        row
        for row in filtered
        if _proposal_matches_filters(
            row,
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
        )
    ]
    filtered = _apply_proposal_cursor(filtered, cursor)
    page = filtered[:limit]
    return copy_records(page), _next_page_cursor(filtered, page, limit)


def _proposal_matches_filters(
    row: ProposalRecord,
    *,
    portfolio_id: Optional[str],
    state: Optional[str],
    created_by: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
) -> bool:
    return all(
        (
            portfolio_id is None or row.portfolio_id == portfolio_id,
            state is None or row.current_state == state,
            created_by is None or row.created_by == created_by,
            created_from is None or row.created_at >= created_from,
            created_to is None or row.created_at <= created_to,
        )
    )


def _apply_proposal_cursor(
    rows: list[ProposalRecord],
    cursor: Optional[str],
) -> list[ProposalRecord]:
    if not cursor:
        return rows

    cursor_index = _proposal_cursor_index(rows, cursor)
    if cursor_index is None:
        return rows
    return rows[cursor_index + 1 :]


def _proposal_cursor_index(rows: list[ProposalRecord], cursor: str) -> int | None:
    for index, row in enumerate(rows):
        if row.proposal_id == cursor:
            return index
    return None


def _next_page_cursor(
    filtered: list[ProposalRecord],
    page: list[ProposalRecord],
    limit: int,
) -> Optional[str]:
    if len(filtered) <= limit or not page:
        return None
    return cast(str, page[-1].proposal_id)


def ordered_memos_for_proposal(
    memos: Iterable[ProposalMemoRecord],
    *,
    proposal_id: str,
) -> list[ProposalMemoRecord]:
    filtered = [memo for memo in memos if memo.proposal_id == proposal_id]
    filtered.sort(key=lambda memo: (memo.proposal_version_no, memo.created_at, memo.memo_id))
    return copy_records(filtered)


def ordered_memos_for_proposals(
    memos: Iterable[ProposalMemoRecord],
    *,
    proposal_ids: list[str],
) -> list[ProposalMemoRecord]:
    if not proposal_ids:
        return []
    proposal_id_set = set(proposal_ids)
    memo_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
    filtered = [memo for memo in memos if memo.proposal_id in proposal_id_set]
    filtered.sort(
        key=lambda memo: (
            memo_order[memo.proposal_id],
            memo.proposal_version_no,
            memo.created_at,
            memo.memo_id,
        )
    )
    return copy_records(filtered)


def ordered_memo_events(
    events: Iterable[ProposalMemoEventRecord],
) -> list[ProposalMemoEventRecord]:
    sorted_events = sorted(events, key=lambda event: (event.occurred_at, event.event_id))
    return copy_records(sorted_events)


def ordered_events_for_proposals(
    event_groups: Iterable[list[ProposalWorkflowEventRecord]],
    *,
    proposal_ids: list[str],
) -> list[ProposalWorkflowEventRecord]:
    if not proposal_ids:
        return []
    proposal_id_set = set(proposal_ids)
    event_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
    events = [
        event
        for proposal_events in event_groups
        for event in proposal_events
        if event.proposal_id in proposal_id_set
    ]
    events.sort(
        key=lambda event: (
            event_order[event.proposal_id],
            event.occurred_at,
            event.event_id,
        )
    )
    return copy_records(events)


def ordered_approvals_for_proposals(
    approval_groups: Iterable[list[ProposalApprovalRecordData]],
    *,
    proposal_ids: list[str],
) -> list[ProposalApprovalRecordData]:
    if not proposal_ids:
        return []
    proposal_id_set = set(proposal_ids)
    approval_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
    approvals = [
        approval
        for proposal_approvals in approval_groups
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
    return copy_records(approvals)


def ordered_versions_for_proposal(
    versions: Iterable[ProposalVersionRecord],
    *,
    proposal_id: str,
) -> list[ProposalVersionRecord]:
    filtered = [version for version in versions if version.proposal_id == proposal_id]
    filtered.sort(key=lambda version: version.version_no)
    return copy_records(filtered)


def current_version_for_proposal(
    versions: Iterable[ProposalVersionRecord],
    *,
    proposal_id: str,
) -> ProposalVersionRecord | None:
    filtered = [version for version in versions if version.proposal_id == proposal_id]
    if not filtered:
        return None
    filtered.sort(key=lambda version: version.version_no, reverse=True)
    return copy_optional(filtered[0])


def recoverable_operations(
    operations: Iterable[ProposalAsyncOperationRecord],
    *,
    as_of: datetime,
    limit: Optional[int],
) -> list[ProposalAsyncOperationRecord]:
    if non_positive_limit(limit):
        return []
    recoverable = recoverable_operation_rows(operations, as_of=as_of)
    recoverable.sort(key=lambda operation: (operation.created_at, operation.operation_id))
    return copy_records(limited_records(recoverable, limit))


def non_positive_limit(limit: Optional[int]) -> bool:
    return limit is not None and limit <= 0


def recoverable_operation_rows(
    operations: Iterable[ProposalAsyncOperationRecord],
    *,
    as_of: datetime,
) -> list[ProposalAsyncOperationRecord]:
    return [operation for operation in operations if operation_is_recoverable(operation, as_of)]


def limited_records(
    records: list[RecordT],
    limit: Optional[int],
) -> list[RecordT]:
    if limit is None:
        return records
    return records[:limit]


def operation_is_recoverable(operation: ProposalAsyncOperationRecord, as_of: datetime) -> bool:
    return operation_is_pending(operation) or running_operation_lease_has_expired(operation, as_of)


def operation_is_pending(operation: ProposalAsyncOperationRecord) -> bool:
    return cast(bool, operation.status == "PENDING")


def running_operation_lease_has_expired(
    operation: ProposalAsyncOperationRecord,
    as_of: datetime,
) -> bool:
    return (
        operation.status == "RUNNING"
        and operation.finished_at is None
        and operation.lease_expires_at is not None
        and operation.lease_expires_at <= as_of
    )


__all__ = [
    "copy_optional",
    "copy_record",
    "copy_records",
    "current_version_for_proposal",
    "filtered_proposal_page",
    "ordered_approvals_for_proposals",
    "ordered_events_for_proposals",
    "ordered_memo_events",
    "ordered_memos_for_proposal",
    "ordered_memos_for_proposals",
    "ordered_versions_for_proposal",
    "limited_records",
    "non_positive_limit",
    "operation_is_pending",
    "operation_is_recoverable",
    "recoverable_operations",
    "recoverable_operation_rows",
    "running_operation_lease_has_expired",
]
