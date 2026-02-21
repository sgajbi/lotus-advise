import os
import warnings
from typing import cast

from src.core.proposals.repository import ProposalRepository
from src.infrastructure.proposals import InMemoryProposalRepository, PostgresProposalRepository


def proposal_store_backend_name() -> str:
    backend = os.getenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY").strip().upper()
    if backend == "POSTGRES":
        return "POSTGRES"
    warnings.warn(
        ("PROPOSAL_STORE_BACKEND legacy runtime backend (IN_MEMORY) is deprecated; use POSTGRES."),
        DeprecationWarning,
        stacklevel=2,
    )
    return "IN_MEMORY"


def proposal_postgres_dsn() -> str:
    return os.getenv("PROPOSAL_POSTGRES_DSN", "").strip()


def build_repository() -> ProposalRepository:
    backend = proposal_store_backend_name()
    if backend == "POSTGRES":
        dsn = proposal_postgres_dsn()
        if not dsn:
            raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
        try:
            return cast(ProposalRepository, PostgresProposalRepository(dsn=dsn))
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("PROPOSAL_POSTGRES_CONNECTION_FAILED") from exc
    return cast(ProposalRepository, InMemoryProposalRepository())
