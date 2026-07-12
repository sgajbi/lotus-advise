from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from typing import Any, Optional

from src.core.proposals.models import ProposalMemoEventRecord, ProposalMemoRecord
from src.infrastructure.proposals.postgres_mappers import (
    json_dump,
    json_dump_list,
    to_memo,
    to_memo_event,
)

ConnectionFactory = Callable[[], Any]


MEMO_COLUMNS = """
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
"""


def create_memo(*, connect: ConnectionFactory, memo: ProposalMemoRecord) -> None:
    with closing(connect()) as connection:
        insert_memo(connection=connection, memo=memo)
        connection.commit()


def insert_memo(*, connection: Any, memo: ProposalMemoRecord) -> None:
    query = f"""
        INSERT INTO proposal_memos (
            {MEMO_COLUMNS}
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    connection.execute(query, _memo_params(memo))


def get_memo(*, connect: ConnectionFactory, memo_id: str) -> Optional[ProposalMemoRecord]:
    query = f"""
        SELECT
            {MEMO_COLUMNS}
        FROM proposal_memos
        WHERE memo_id = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (memo_id,)).fetchone()
    return to_memo(row)


def get_memo_by_proposal_version(
    *,
    connect: ConnectionFactory,
    proposal_id: str,
    proposal_version_no: int,
) -> Optional[ProposalMemoRecord]:
    query = f"""
        SELECT
            {MEMO_COLUMNS}
        FROM proposal_memos
        WHERE proposal_id = %s AND proposal_version_no = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (proposal_id, proposal_version_no)).fetchone()
    return to_memo(row)


def list_memos(*, connect: ConnectionFactory, proposal_id: str) -> list[ProposalMemoRecord]:
    query = f"""
        SELECT
            {MEMO_COLUMNS}
        FROM proposal_memos
        WHERE proposal_id = %s
        ORDER BY proposal_version_no ASC, created_at ASC, memo_id ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_id,)).fetchall()
    return [memo for row in rows if (memo := to_memo(row)) is not None]


def list_memos_for_proposals(
    *,
    connect: ConnectionFactory,
    proposal_ids: list[str],
) -> list[ProposalMemoRecord]:
    if not proposal_ids:
        return []
    query = f"""
        SELECT
            {MEMO_COLUMNS}
        FROM proposal_memos
        WHERE proposal_id = ANY(%s)
        ORDER BY proposal_id ASC, proposal_version_no ASC, created_at ASC, memo_id ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_ids,)).fetchall()
    memo_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
    memos = [memo for row in rows if (memo := to_memo(row)) is not None]
    return sorted(
        memos,
        key=lambda memo: (
            memo_order.get(memo.proposal_id, len(memo_order)),
            memo.proposal_version_no,
            memo.created_at,
            memo.memo_id,
        ),
    )


def append_memo_event(*, connect: ConnectionFactory, event: ProposalMemoEventRecord) -> None:
    with closing(connect()) as connection:
        insert_memo_event(connection=connection, event=event)
        connection.commit()


def insert_memo_event(*, connection: Any, event: ProposalMemoEventRecord) -> None:
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
            json_dump(event.reason_json),
        ),
    )


def list_memo_events(
    *,
    connect: ConnectionFactory,
    memo_id: str,
) -> list[ProposalMemoEventRecord]:
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
    with closing(connect()) as connection:
        rows = connection.execute(query, (memo_id,)).fetchall()
    return [to_memo_event(row) for row in rows]


def _memo_params(memo: ProposalMemoRecord) -> tuple[object, ...]:
    return (
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
        json_dump(memo.memo_json),
        json_dump(memo.projection_json),
        json_dump_list(memo.review_events_json),
        json_dump_list(memo.report_package_events_json),
        json_dump_list(memo.archive_refs_json),
        json_dump_list(memo.ai_refs_json),
        json_dump(memo.replay_metadata_json),
    )


__all__ = [
    "append_memo_event",
    "create_memo",
    "get_memo",
    "get_memo_by_proposal_version",
    "insert_memo",
    "insert_memo_event",
    "list_memo_events",
    "list_memos",
    "list_memos_for_proposals",
]
