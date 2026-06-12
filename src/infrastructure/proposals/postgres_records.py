from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
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


@dataclass
class _ProposalListFilterSql:
    where_clauses: list[str]
    args: list[object]
    cursor_where_clauses: list[str]
    cursor_args: list[object]


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
    filters = _proposal_list_filter_sql(
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
    )
    _apply_proposal_list_cursor(filters, cursor=cursor)
    query = _proposal_list_query(filters.where_clauses)
    args = [*filters.args, limit + 1]
    with closing(connect()) as connection:
        rows = connection.execute(query, tuple(args)).fetchall()
    return _proposal_list_page(rows, limit=limit)


def _proposal_list_filter_sql(
    *,
    portfolio_id: Optional[str],
    state: Optional[str],
    created_by: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
) -> _ProposalListFilterSql:
    filters = _ProposalListFilterSql(
        where_clauses=[],
        args=[],
        cursor_where_clauses=["cursor_record.proposal_id = %s"],
        cursor_args=[],
    )
    for value, clause, cursor_clause in _proposal_list_filter_specs(
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
    ):
        if value is not None:
            _add_proposal_list_filter(filters, clause, cursor_clause, value)
    return filters


def _proposal_list_filter_specs(
    *,
    portfolio_id: Optional[str],
    state: Optional[str],
    created_by: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
) -> tuple[tuple[object | None, str, str], ...]:
    return (
        (portfolio_id, "portfolio_id = %s", "cursor_record.portfolio_id = %s"),
        (state, "current_state = %s", "cursor_record.current_state = %s"),
        (created_by, "created_by = %s", "cursor_record.created_by = %s"),
        (
            created_from.isoformat() if created_from is not None else None,
            "created_at >= %s",
            "cursor_record.created_at >= %s",
        ),
        (
            created_to.isoformat() if created_to is not None else None,
            "created_at <= %s",
            "cursor_record.created_at <= %s",
        ),
    )


def _add_proposal_list_filter(
    filters: _ProposalListFilterSql,
    clause: str,
    cursor_clause: str,
    value: object,
) -> None:
    filters.where_clauses.append(clause)
    filters.args.append(value)
    filters.cursor_where_clauses.append(cursor_clause)
    filters.cursor_args.append(value)


def _apply_proposal_list_cursor(filters: _ProposalListFilterSql, *, cursor: Optional[str]) -> None:
    if not cursor:
        return
    filters.where_clauses.append(_proposal_list_cursor_clause(filters.cursor_where_clauses))
    filters.args.extend((cursor, *filters.cursor_args))


def _proposal_list_cursor_clause(cursor_where_clauses: list[str]) -> str:
    cursor_where_sql = " AND ".join(cursor_where_clauses)
    return f"""
            (created_at, proposal_id) < (
                SELECT cursor_record.created_at, cursor_record.proposal_id
                FROM proposal_records cursor_record
                WHERE {cursor_where_sql}
            )
            """


def _proposal_list_query(where_clauses: list[str]) -> str:
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return f"""
        SELECT
            {PROPOSAL_COLUMNS}
        FROM proposal_records
        {where_sql}
        ORDER BY created_at DESC, proposal_id DESC
        LIMIT %s
    """


def _proposal_list_page(
    rows: list[object], *, limit: int
) -> tuple[list[ProposalRecord], Optional[str]]:
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
