import os
import warnings

from src.infrastructure.dpm_runs import (
    InMemoryDpmRunRepository,
    PostgresDpmRunRepository,
    SqliteDpmRunRepository,
)


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 1 else default


def env_non_negative_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def env_csv_set(name: str, default: set[str]) -> set[str]:
    value = os.getenv(name)
    if value is None:
        return set(default)
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or set(default)


def artifact_store_mode() -> str:
    mode = os.getenv("DPM_ARTIFACT_STORE_MODE", "DERIVED").strip().upper()
    return "PERSISTED" if mode == "PERSISTED" else "DERIVED"


def supportability_store_backend_name() -> str:
    backend = os.getenv("DPM_SUPPORTABILITY_STORE_BACKEND", "IN_MEMORY").strip().upper()
    if backend == "POSTGRES":
        return "POSTGRES"
    warnings.warn(
        (
            "DPM_SUPPORTABILITY_STORE_BACKEND legacy runtime backends "
            "(IN_MEMORY/SQL/SQLITE) are deprecated; use POSTGRES."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return "SQL" if backend in {"SQL", "SQLITE"} else "IN_MEMORY"


def supportability_sql_path() -> str:
    return os.getenv(
        "DPM_SUPPORTABILITY_SQL_PATH",
        os.getenv("DPM_SUPPORTABILITY_SQLITE_PATH", ".data/dpm_supportability.db"),
    )


def supportability_postgres_dsn() -> str:
    return os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "").strip()


def build_repository():
    backend = supportability_store_backend_name()
    if backend == "SQL":
        return SqliteDpmRunRepository(database_path=supportability_sql_path())
    if backend == "POSTGRES":
        dsn = supportability_postgres_dsn()
        if not dsn:
            raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")
        try:
            return PostgresDpmRunRepository(dsn=dsn)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED") from exc
    return InMemoryDpmRunRepository()
