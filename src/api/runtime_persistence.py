from __future__ import annotations

from src.api.proposals.runtime import (
    policy_postgres_dsn,
    policy_store_backend_name,
    proposal_postgres_dsn,
    proposal_store_backend_name,
)
from src.runtime.workspace_repositories import (
    workspace_configured_postgres_dsn,
    workspace_store_backend_name,
)


def validate_advisory_runtime_persistence() -> None:
    if proposal_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES")
    if not proposal_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN")
    if policy_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_POLICY_POSTGRES")
    if not policy_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_POLICY_POSTGRES_DSN")
    if workspace_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_WORKSPACE_POSTGRES")
    if not workspace_configured_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_WORKSPACE_POSTGRES_DSN")
