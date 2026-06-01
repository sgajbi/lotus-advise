from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from typing import Any, Optional

from src.core.proposals.models import ProposalVersionRecord
from src.infrastructure.proposals.postgres_mappers import json_dump, optional_json, to_version

ConnectionFactory = Callable[[], Any]


VERSION_COLUMNS = """
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
"""


def create_version(*, connect: ConnectionFactory, version: ProposalVersionRecord) -> None:
    query = f"""
        INSERT INTO proposal_versions (
            {VERSION_COLUMNS}
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
    with closing(connect()) as connection:
        connection.execute(query, _version_params(version))
        connection.commit()


def get_version(
    *,
    connect: ConnectionFactory,
    proposal_id: str,
    version_no: int,
) -> Optional[ProposalVersionRecord]:
    query = f"""
        SELECT
            {VERSION_COLUMNS}
        FROM proposal_versions
        WHERE proposal_id = %s AND version_no = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (proposal_id, version_no)).fetchone()
    return to_version(row)


def list_versions(*, connect: ConnectionFactory, proposal_id: str) -> list[ProposalVersionRecord]:
    query = f"""
        SELECT
            {VERSION_COLUMNS}
        FROM proposal_versions
        WHERE proposal_id = %s
        ORDER BY version_no ASC
    """
    with closing(connect()) as connection:
        rows = connection.execute(query, (proposal_id,)).fetchall()
    return [version for row in rows if (version := to_version(row)) is not None]


def get_current_version(
    *,
    connect: ConnectionFactory,
    proposal_id: str,
) -> Optional[ProposalVersionRecord]:
    query = f"""
        SELECT
            {VERSION_COLUMNS}
        FROM proposal_versions
        WHERE proposal_id = %s
        ORDER BY version_no DESC
        LIMIT 1
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (proposal_id,)).fetchone()
    return to_version(row)


def _version_params(version: ProposalVersionRecord) -> tuple[object, ...]:
    return (
        version.proposal_version_id,
        version.proposal_id,
        version.version_no,
        version.created_at.isoformat(),
        version.request_hash,
        version.artifact_hash,
        version.simulation_hash,
        version.status_at_creation,
        json_dump(version.proposal_result_json),
        json_dump(version.artifact_json),
        json_dump(version.evidence_bundle_json),
        optional_json(version.gate_decision_json),
    )


__all__ = [
    "create_version",
    "get_current_version",
    "get_version",
    "list_versions",
]
