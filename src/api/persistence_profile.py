from __future__ import annotations

import os

from src.api.routers.proposals_config import proposal_postgres_dsn, proposal_store_backend_name


_PRODUCTION_PROFILE = "PRODUCTION"
_LOCAL_PROFILE = "LOCAL"


def app_persistence_profile_name() -> str:
    profile = os.getenv("APP_PERSISTENCE_PROFILE", _LOCAL_PROFILE).strip().upper()
    return _PRODUCTION_PROFILE if profile == _PRODUCTION_PROFILE else _LOCAL_PROFILE


def validate_persistence_profile_guardrails() -> None:
    if app_persistence_profile_name() != _PRODUCTION_PROFILE:
        return
    if proposal_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES")
    if not proposal_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN")
