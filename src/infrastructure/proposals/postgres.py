import json
from contextlib import closing
from datetime import datetime
from importlib.util import find_spec
from typing import Optional

from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalVersionRecord,
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
        query = """
            SELECT
                idempotency_key,
                request_hash,
                proposal_id,
                proposal_version_no,
                created_at
            FROM proposal_idempotency
            WHERE idempotency_key = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (idempotency_key,)).fetchone()
        if row is None:
            return None
        return ProposalIdempotencyRecord(
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            proposal_id=row["proposal_id"],
            proposal_version_no=int(row["proposal_version_no"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_idempotency(self, record: ProposalIdempotencyRecord) -> None:
        query = """
            INSERT INTO proposal_idempotency (
                idempotency_key,
                request_hash,
                proposal_id,
                proposal_version_no,
                created_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO UPDATE SET
                request_hash=excluded.request_hash,
                proposal_id=excluded.proposal_id,
                proposal_version_no=excluded.proposal_version_no,
                created_at=excluded.created_at
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    record.idempotency_key,
                    record.request_hash,
                    record.proposal_id,
                    record.proposal_version_no,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def update_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def get_operation(self, *, operation_id: str) -> Optional[ProposalAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                idempotency_key,
                proposal_id,
                created_by,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json
            FROM proposal_async_operations
            WHERE operation_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (operation_id,)).fetchone()
        return _to_operation(row)

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                idempotency_key,
                proposal_id,
                created_by,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json
            FROM proposal_async_operations
            WHERE correlation_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return _to_operation(row)

    def create_proposal(self, proposal: ProposalRecord) -> None:
        self._upsert_proposal(proposal)

    def update_proposal(self, proposal: ProposalRecord) -> None:
        self._upsert_proposal(proposal)

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
                advisor_notes
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
        args: list[str] = []
        if portfolio_id is not None:
            where_clauses.append("portfolio_id = %s")
            args.append(portfolio_id)
        if state is not None:
            where_clauses.append("current_state = %s")
            args.append(state)
        if created_by is not None:
            where_clauses.append("created_by = %s")
            args.append(created_by)
        if created_from is not None:
            where_clauses.append("created_at >= %s")
            args.append(created_from.isoformat())
        if created_to is not None:
            where_clauses.append("created_at <= %s")
            args.append(created_to.isoformat())
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
                advisor_notes
            FROM proposal_records
            {where_sql}
            ORDER BY created_at DESC, proposal_id DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        proposals = [_to_proposal(row) for row in rows]
        proposals = [proposal for proposal in proposals if proposal is not None]
        if cursor:
            cursor_index = next(
                (
                    index
                    for index, proposal in enumerate(proposals)
                    if proposal.proposal_id == cursor
                ),
                None,
            )
            if cursor_index is None:
                return [], None
            proposals = proposals[cursor_index + 1 :]
        page = proposals[:limit]
        next_cursor = page[-1].proposal_id if len(proposals) > limit else None
        return page, next_cursor

    def create_version(self, version: ProposalVersionRecord) -> None:
        query = """
            INSERT INTO proposal_versions (
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
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    version.proposal_version_id,
                    version.proposal_id,
                    version.version_no,
                    version.created_at.isoformat(),
                    version.request_hash,
                    version.artifact_hash,
                    version.simulation_hash,
                    version.status_at_creation,
                    _json_dump(version.proposal_result_json),
                    _json_dump(version.artifact_json),
                    _json_dump(version.evidence_bundle_json),
                    _optional_json(version.gate_decision_json),
                ),
            )
            connection.commit()

    def get_version(self, *, proposal_id: str, version_no: int) -> Optional[ProposalVersionRecord]:
        query = """
            SELECT
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
            FROM proposal_versions
            WHERE proposal_id = %s AND version_no = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (proposal_id, version_no)).fetchone()
        return _to_version(row)

    def get_current_version(self, *, proposal_id: str) -> Optional[ProposalVersionRecord]:
        query = """
            SELECT
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
            FROM proposal_versions
            WHERE proposal_id = %s
            ORDER BY version_no DESC
            LIMIT 1
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (proposal_id,)).fetchone()
        return _to_version(row)

    def __getattr__(self, _name: str):
        raise RuntimeError("PROPOSAL_POSTGRES_NOT_IMPLEMENTED")

    def _connect(self):
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    proposal_version_no INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_async_operations (
                    operation_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correlation_id TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT NULL,
                    proposal_id TEXT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT NULL,
                    finished_at TEXT NULL,
                    result_json TEXT NULL,
                    error_json TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_records (
                    proposal_id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    mandate_id TEXT NULL,
                    jurisdiction TEXT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_event_at TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    current_version_no INTEGER NOT NULL,
                    title TEXT NULL,
                    advisor_notes TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_versions (
                    proposal_version_id TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    version_no INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL,
                    simulation_hash TEXT NOT NULL,
                    status_at_creation TEXT NOT NULL,
                    proposal_result_json TEXT NOT NULL,
                    artifact_json TEXT NOT NULL,
                    evidence_bundle_json TEXT NOT NULL,
                    gate_decision_json TEXT NULL,
                    PRIMARY KEY (proposal_id, version_no)
                )
                """
            )
            connection.commit()

    def _upsert_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        query = """
            INSERT INTO proposal_async_operations (
                operation_id,
                operation_type,
                status,
                correlation_id,
                idempotency_key,
                proposal_id,
                created_by,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (operation_id) DO UPDATE SET
                operation_type=excluded.operation_type,
                status=excluded.status,
                correlation_id=excluded.correlation_id,
                idempotency_key=excluded.idempotency_key,
                proposal_id=excluded.proposal_id,
                created_by=excluded.created_by,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                result_json=excluded.result_json,
                error_json=excluded.error_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    operation.operation_id,
                    operation.operation_type,
                    operation.status,
                    operation.correlation_id,
                    operation.idempotency_key,
                    operation.proposal_id,
                    operation.created_by,
                    operation.created_at.isoformat(),
                    _optional_iso(operation.started_at),
                    _optional_iso(operation.finished_at),
                    _optional_json(operation.result_json),
                    _optional_json(operation.error_json),
                ),
            )
            connection.commit()

    def _upsert_proposal(self, proposal: ProposalRecord) -> None:
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
                advisor_notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                advisor_notes=excluded.advisor_notes
        """
        with closing(self._connect()) as connection:
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
                ),
            )
            connection.commit()


def _import_psycopg():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


def _optional_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _optional_json(value: Optional[dict]) -> Optional[str]:
    if value is None:
        return None
    return _json_dump(value)


def _json_dump(value: dict) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _to_operation(row) -> Optional[ProposalAsyncOperationRecord]:
    if row is None:
        return None
    return ProposalAsyncOperationRecord(
        operation_id=row["operation_id"],
        operation_type=row["operation_type"],
        status=row["status"],
        correlation_id=row["correlation_id"],
        idempotency_key=row["idempotency_key"],
        proposal_id=row["proposal_id"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=_optional_datetime(row["started_at"]),
        finished_at=_optional_datetime(row["finished_at"]),
        result_json=_optional_load_json(row["result_json"]),
        error_json=_optional_load_json(row["error_json"]),
    )


def _optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _optional_load_json(value: Optional[str]) -> Optional[dict]:
    if value is None:
        return None
    return json.loads(value)


def _to_proposal(row) -> Optional[ProposalRecord]:
    if row is None:
        return None
    return ProposalRecord(
        proposal_id=row["proposal_id"],
        portfolio_id=row["portfolio_id"],
        mandate_id=row["mandate_id"],
        jurisdiction=row["jurisdiction"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_event_at=datetime.fromisoformat(row["last_event_at"]),
        current_state=row["current_state"],
        current_version_no=int(row["current_version_no"]),
        title=row["title"],
        advisor_notes=row["advisor_notes"],
    )


def _to_version(row) -> Optional[ProposalVersionRecord]:
    if row is None:
        return None
    return ProposalVersionRecord(
        proposal_version_id=row["proposal_version_id"],
        proposal_id=row["proposal_id"],
        version_no=int(row["version_no"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        request_hash=row["request_hash"],
        artifact_hash=row["artifact_hash"],
        simulation_hash=row["simulation_hash"],
        status_at_creation=row["status_at_creation"],
        proposal_result_json=json.loads(row["proposal_result_json"]),
        artifact_json=json.loads(row["artifact_json"]),
        evidence_bundle_json=json.loads(row["evidence_bundle_json"]),
        gate_decision_json=_optional_load_json(row["gate_decision_json"]),
    )
