from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from typing import Any, Optional, cast

from src.core.proposals.models import ProposalRecord
from src.infrastructure.proposals.postgres_mappers import to_proposal

ConnectionFactory = Callable[[], Any]


PROPOSAL_COLUMNS = """
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
"""


def create_proposal(*, connect: ConnectionFactory, proposal: ProposalRecord) -> None:
    with closing(connect()) as connection:
        upsert_proposal(connection=connection, proposal=proposal)
        connection.commit()


def update_proposal(*, connect: ConnectionFactory, proposal: ProposalRecord) -> None:
    with closing(connect()) as connection:
        upsert_proposal(connection=connection, proposal=proposal)
        connection.commit()


def get_proposal(*, connect: ConnectionFactory, proposal_id: str) -> Optional[ProposalRecord]:
    query = f"""
        SELECT
            {PROPOSAL_COLUMNS}
        FROM proposal_records
        WHERE proposal_id = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (proposal_id,)).fetchone()
    return to_proposal(row)


def list_proposals(
    *,
    connect: ConnectionFactory,
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
            {PROPOSAL_COLUMNS}
        FROM proposal_records
        {where_sql}
        ORDER BY created_at DESC, proposal_id DESC
        LIMIT %s
    """
    args.append(limit + 1)
    with closing(connect()) as connection:
        rows = connection.execute(query, tuple(args)).fetchall()
    proposals = cast(
        list[ProposalRecord],
        [proposal for proposal in (to_proposal(row) for row in rows) if proposal is not None],
    )
    page = proposals[:limit]
    next_cursor = page[-1].proposal_id if len(proposals) > limit else None
    return page, next_cursor


def upsert_proposal(*, connection: Any, proposal: ProposalRecord) -> None:
    query = f"""
        INSERT INTO proposal_records (
            {PROPOSAL_COLUMNS}
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


__all__ = [
    "create_proposal",
    "get_proposal",
    "list_proposals",
    "update_proposal",
    "upsert_proposal",
]
