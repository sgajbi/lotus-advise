from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from typing import Any

from src.core.proposals.models import ProposalWorkflowEventRecord
from src.infrastructure.proposals.postgres_mappers import json_dump, to_event

ConnectionFactory = Callable[[], Any]


EVENT_COLUMNS = """
    event_id,
    proposal_id,
    event_type,
    from_state,
    to_state,
    actor_id,
    occurred_at,
    reason_json,
    related_version_no
"""


def append_event(*, connect: ConnectionFactory, event: ProposalWorkflowEventRecord) -> None:
    with closing(connect()) as connection:
        insert_event(connection=connection, event=event)
        connection.commit()


def list_events(
    *,
    connect: ConnectionFactory,
    proposal_id: str,
) -> list[ProposalWorkflowEventRecord]:
    query = f"""
        SELECT
            {EVENT_COLUMNS}
        FROM proposal_workflow_events
        WHERE proposal_id = %s
        ORDER BY occurred_at ASC, event_id ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_id,)).fetchall()
    return [to_event(row) for row in rows]


def list_events_for_proposals(
    *,
    connect: ConnectionFactory,
    proposal_ids: list[str],
) -> list[ProposalWorkflowEventRecord]:
    if not proposal_ids:
        return []
    query = f"""
        SELECT
            {EVENT_COLUMNS}
        FROM proposal_workflow_events
        WHERE proposal_id = ANY(%s)
        ORDER BY proposal_id ASC, occurred_at ASC, event_id ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_ids,)).fetchall()
    event_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
    events = [to_event(row) for row in rows]
    return sorted(
        events,
        key=lambda event: (
            event_order.get(event.proposal_id, len(event_order)),
            event.occurred_at,
            event.event_id,
        ),
    )


def insert_event(*, connection: Any, event: ProposalWorkflowEventRecord) -> None:
    query = f"""
        INSERT INTO proposal_workflow_events (
            {EVENT_COLUMNS}
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
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
            json_dump(event.reason_json),
            event.related_version_no,
        ),
    )
    existing = _get_event(connection=connection, event_id=event.event_id)
    if existing != event:
        raise ValueError("PROPOSAL_WORKFLOW_EVENT_IDENTITY_CONFLICT")


def _get_event(*, connection: Any, event_id: str) -> ProposalWorkflowEventRecord | None:
    query = f"""
        SELECT
            {EVENT_COLUMNS}
        FROM proposal_workflow_events
        WHERE event_id = %s
    """
    row = connection.execute(query, (event_id,)).fetchone()
    if row is None:
        return None
    return to_event(row)


__all__ = [
    "append_event",
    "insert_event",
    "list_events",
    "list_events_for_proposals",
]
