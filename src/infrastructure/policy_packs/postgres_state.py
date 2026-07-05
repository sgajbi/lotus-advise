from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import closing
from typing import Any

from src.infrastructure.proposals.postgres_mappers import json_dump

ConnectionFactory = Callable[[], Any]


class PostgresPolicyEvaluationStateStore:
    def __init__(self, *, connect: ConnectionFactory) -> None:
        self._connect = connect

    def load_snapshot(self) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            record_rows = connection.execute(
                """
                SELECT evaluation_id, record_json
                FROM policy_evaluation_records
                ORDER BY generated_at ASC, evaluation_id ASC
                """
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT evaluation_id, event_json
                FROM policy_evaluation_audit_events
                ORDER BY evaluation_id ASC, occurred_at ASC, event_id ASC
                """
            ).fetchall()
            idempotency_rows = connection.execute(
                """
                SELECT idempotency_key, request_hash, evaluation_id, event_id
                FROM policy_evaluation_idempotency
                ORDER BY idempotency_key ASC
                """
            ).fetchall()
        return {
            "records": _records_snapshot(record_rows),
            "events": _events_snapshot(event_rows),
            "idempotency": [dict(row) for row in idempotency_rows],
            "identity_index": [],
        }

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        with closing(self._connect()) as connection:
            for record in snapshot.get("records", {}).values():
                _upsert_policy_evaluation_record(connection=connection, record=record)
            for events in snapshot.get("events", {}).values():
                for event in events:
                    _upsert_policy_evaluation_event(connection=connection, event=event)
            for idempotency in snapshot.get("idempotency", []):
                _upsert_policy_evaluation_idempotency(
                    connection=connection,
                    idempotency=idempotency,
                    created_at=_event_created_at(snapshot=snapshot, idempotency=idempotency),
                )
            connection.commit()


class PostgresPolicyPackCatalogStateStore:
    def __init__(self, *, connect: ConnectionFactory) -> None:
        self._connect = connect

    def load_snapshot(self) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            definition_rows = connection.execute(
                """
                SELECT definition_json
                FROM policy_pack_catalog_versions
                ORDER BY policy_pack_id ASC, policy_version ASC
                """
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT event_json
                FROM policy_pack_catalog_audit_events
                ORDER BY policy_pack_id ASC, policy_version ASC, occurred_at ASC, event_id ASC
                """
            ).fetchall()
            idempotency_rows = connection.execute(
                """
                SELECT idempotency_key, request_hash, policy_pack_id, policy_version, event_id
                FROM policy_pack_catalog_idempotency
                ORDER BY idempotency_key ASC
                """
            ).fetchall()
        return {
            "definitions": [json.loads(row["definition_json"]) for row in definition_rows],
            "events": [json.loads(row["event_json"]) for row in event_rows],
            "idempotency": [dict(row) for row in idempotency_rows],
        }

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        with closing(self._connect()) as connection:
            for definition in snapshot.get("definitions", []):
                _upsert_policy_pack_catalog_version(
                    connection=connection,
                    definition=definition,
                )
            for event in snapshot.get("events", []):
                _upsert_policy_pack_catalog_event(connection=connection, event=event)
            for idempotency in snapshot.get("idempotency", []):
                _upsert_policy_pack_catalog_idempotency(
                    connection=connection,
                    idempotency=idempotency,
                    created_at=_catalog_event_created_at(
                        snapshot=snapshot,
                        idempotency=idempotency,
                    ),
                )
            connection.commit()


def _records_snapshot(rows: list[Any]) -> dict[str, dict[str, Any]]:
    return {str(row["evaluation_id"]): json.loads(row["record_json"]) for row in rows}


def _events_snapshot(rows: list[Any]) -> dict[str, list[dict[str, Any]]]:
    events: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        events.setdefault(str(row["evaluation_id"]), []).append(json.loads(row["event_json"]))
    return events


def _upsert_policy_evaluation_record(*, connection: Any, record: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO policy_evaluation_records (
            evaluation_id,
            proposal_id,
            proposal_version_id,
            portfolio_id,
            policy_pack_id,
            policy_version,
            generated_at,
            evaluation_status,
            source_evidence_hash,
            policy_content_hash,
            evaluation_hash,
            record_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (evaluation_id) DO UPDATE SET
            evaluation_status=excluded.evaluation_status,
            record_json=excluded.record_json
        """,
        (
            record["evaluation_id"],
            record["proposal_id"],
            record["proposal_version_id"],
            record["portfolio_id"],
            record["policy_pack_id"],
            record["policy_version"],
            record["generated_at"],
            record["evaluation_status"],
            record["source_evidence_hash"],
            record["policy_content_hash"],
            record["evaluation_hash"],
            json_dump(record),
        ),
    )


def _upsert_policy_evaluation_event(*, connection: Any, event: dict[str, Any]) -> None:
    reason = event.get("reason_json", {})
    connection.execute(
        """
        INSERT INTO policy_evaluation_audit_events (
            evaluation_id,
            event_id,
            event_type,
            actor_id,
            occurred_at,
            idempotency_key,
            request_hash,
            event_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (evaluation_id, event_id) DO UPDATE SET
            event_json=excluded.event_json
        """,
        (
            event["evaluation_id"],
            event["event_id"],
            event["event_type"],
            event["actor_id"],
            event["occurred_at"],
            event.get("idempotency_key"),
            reason.get("idempotency_request_hash", ""),
            json_dump(event),
        ),
    )


def _upsert_policy_evaluation_idempotency(
    *, connection: Any, idempotency: dict[str, Any], created_at: str
) -> None:
    connection.execute(
        """
        INSERT INTO policy_evaluation_idempotency (
            idempotency_key,
            request_hash,
            evaluation_id,
            event_id,
            created_at
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO UPDATE SET
            request_hash=excluded.request_hash,
            evaluation_id=excluded.evaluation_id,
            event_id=excluded.event_id
        """,
        (
            idempotency["idempotency_key"],
            idempotency["request_hash"],
            idempotency["evaluation_id"],
            idempotency["event_id"],
            created_at,
        ),
    )


def _upsert_policy_pack_catalog_version(*, connection: Any, definition: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO policy_pack_catalog_versions (
            policy_pack_id,
            policy_version,
            activation_state,
            content_hash,
            definition_json
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (policy_pack_id, policy_version) DO UPDATE SET
            activation_state=excluded.activation_state,
            content_hash=excluded.content_hash,
            definition_json=excluded.definition_json
        """,
        (
            definition["policy_pack_id"],
            definition["policy_version"],
            definition["activation_state"],
            definition["content_hash"],
            json_dump(definition),
        ),
    )


def _upsert_policy_pack_catalog_event(*, connection: Any, event: dict[str, Any]) -> None:
    reason = event.get("reason", {})
    connection.execute(
        """
        INSERT INTO policy_pack_catalog_audit_events (
            policy_pack_id,
            policy_version,
            event_id,
            event_type,
            actor_id,
            occurred_at,
            idempotency_key,
            request_hash,
            event_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (policy_pack_id, policy_version, event_id) DO UPDATE SET
            event_json=excluded.event_json
        """,
        (
            event["policy_pack_id"],
            event["policy_version"],
            event["event_id"],
            event["event_type"],
            event["actor_id"],
            event["occurred_at"],
            event.get("idempotency_key"),
            reason.get("idempotency_request_hash", ""),
            json_dump(event),
        ),
    )


def _upsert_policy_pack_catalog_idempotency(
    *, connection: Any, idempotency: dict[str, Any], created_at: str
) -> None:
    connection.execute(
        """
        INSERT INTO policy_pack_catalog_idempotency (
            idempotency_key,
            request_hash,
            policy_pack_id,
            policy_version,
            event_id,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO UPDATE SET
            request_hash=excluded.request_hash,
            policy_pack_id=excluded.policy_pack_id,
            policy_version=excluded.policy_version,
            event_id=excluded.event_id
        """,
        (
            idempotency["idempotency_key"],
            idempotency["request_hash"],
            idempotency["policy_pack_id"],
            idempotency["policy_version"],
            idempotency["event_id"],
            created_at,
        ),
    )


def _event_created_at(*, snapshot: dict[str, Any], idempotency: dict[str, Any]) -> str:
    for event in snapshot.get("events", {}).get(str(idempotency["evaluation_id"]), []):
        if event["event_id"] == idempotency["event_id"]:
            return str(event["occurred_at"])
    return ""


def _catalog_event_created_at(*, snapshot: dict[str, Any], idempotency: dict[str, Any]) -> str:
    for event in snapshot.get("events", []):
        if (
            event["policy_pack_id"] == idempotency["policy_pack_id"]
            and event["policy_version"] == idempotency["policy_version"]
            and event["event_id"] == idempotency["event_id"]
        ):
            return str(event["occurred_at"])
    return ""


__all__ = [
    "PostgresPolicyEvaluationStateStore",
    "PostgresPolicyPackCatalogStateStore",
]
