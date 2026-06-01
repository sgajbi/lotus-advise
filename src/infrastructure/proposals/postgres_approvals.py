from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from typing import Any

from src.core.proposals.models import ProposalApprovalRecordData
from src.infrastructure.proposals.postgres_mappers import json_dump, to_approval

ConnectionFactory = Callable[[], Any]


APPROVAL_COLUMNS = """
    approval_id,
    proposal_id,
    approval_type,
    approved,
    actor_id,
    occurred_at,
    details_json,
    related_version_no
"""


def create_approval(*, connect: ConnectionFactory, approval: ProposalApprovalRecordData) -> None:
    with closing(connect()) as connection:
        insert_approval(connection=connection, approval=approval)
        connection.commit()


def list_approvals(
    *,
    connect: ConnectionFactory,
    proposal_id: str,
) -> list[ProposalApprovalRecordData]:
    query = f"""
        SELECT
            {APPROVAL_COLUMNS}
        FROM proposal_approvals
        WHERE proposal_id = %s
        ORDER BY occurred_at ASC, approval_id ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_id,)).fetchall()
    return [to_approval(row) for row in rows]


def list_approvals_for_proposals(
    *,
    connect: ConnectionFactory,
    proposal_ids: list[str],
) -> list[ProposalApprovalRecordData]:
    if not proposal_ids:
        return []
    query = f"""
        SELECT
            {APPROVAL_COLUMNS}
        FROM proposal_approvals
        WHERE proposal_id = ANY(%s)
        ORDER BY proposal_id ASC, occurred_at ASC, approval_id ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_ids,)).fetchall()
    approval_order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
    approvals = [to_approval(row) for row in rows]
    return sorted(
        approvals,
        key=lambda approval: (
            approval_order.get(approval.proposal_id, len(approval_order)),
            approval.occurred_at,
            approval.approval_id,
        ),
    )


def insert_approval(*, connection: Any, approval: ProposalApprovalRecordData) -> None:
    query = f"""
        INSERT INTO proposal_approvals (
            {APPROVAL_COLUMNS}
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
            json_dump(approval.details_json),
            approval.related_version_no,
        ),
    )


__all__ = [
    "create_approval",
    "insert_approval",
    "list_approvals",
    "list_approvals_for_proposals",
]
