from __future__ import annotations

from contextlib import closing
from importlib.util import find_spec
from typing import Any

from src.core.policy_packs.durable_repositories import (
    DurablePolicyEvaluationRepository,
    DurablePolicyPackCatalogRepository,
)
from src.infrastructure.policy_packs.postgres_state import (
    PostgresPolicyEvaluationStateStore,
    PostgresPolicyPackCatalogStateStore,
)
from src.infrastructure.postgres_migrations import apply_postgres_migrations


class PostgresPolicyEvaluationRepository(DurablePolicyEvaluationRepository):
    def __init__(self, *, dsn: str) -> None:
        self._dsn = _validated_dsn(dsn)
        self._init_db()
        super().__init__(state_store=PostgresPolicyEvaluationStateStore(connect=self._connect))

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="policy_packs")


class PostgresPolicyPackCatalogRepository(DurablePolicyPackCatalogRepository):
    def __init__(self, *, dsn: str) -> None:
        self._dsn = _validated_dsn(dsn)
        self._init_db()
        super().__init__(state_store=PostgresPolicyPackCatalogStateStore(connect=self._connect))

    def _connect(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="policy_packs")


def _validated_dsn(dsn: str) -> str:
    if not dsn:
        raise RuntimeError("POLICY_POSTGRES_DSN_REQUIRED")
    if find_spec("psycopg") is None:
        raise RuntimeError("POLICY_POSTGRES_DRIVER_MISSING")
    return dsn


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


__all__ = [
    "PostgresPolicyEvaluationRepository",
    "PostgresPolicyPackCatalogRepository",
]
