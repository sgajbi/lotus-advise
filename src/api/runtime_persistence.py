from __future__ import annotations

from src.api.proposals.runtime import proposal_postgres_dsn, proposal_store_backend_name


def validate_advisory_runtime_persistence() -> None:
    if proposal_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES")
    if not proposal_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN")
