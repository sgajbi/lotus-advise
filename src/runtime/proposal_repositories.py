import importlib
import os
from typing import Callable, cast

from src.core.proposals.repository import ProposalRepository

ProposalRepositoryFactory = Callable[..., ProposalRepository]

PostgresProposalRepository: ProposalRepositoryFactory | None = None


def proposal_store_backend_name() -> str:
    backend = os.getenv("PROPOSAL_STORE_BACKEND", "POSTGRES").strip().upper()
    if backend != "POSTGRES":
        raise RuntimeError("PROPOSAL_STORE_BACKEND_UNSUPPORTED")
    return backend


def proposal_postgres_dsn() -> str:
    return os.getenv("PROPOSAL_POSTGRES_DSN", "").strip()


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [
        ConnectionError,
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
    ]
    try:
        import psycopg
    except ImportError:
        pass
    else:
        types.append(psycopg.Error)
    return tuple(types)


def _postgres_repository_factory() -> ProposalRepositoryFactory:
    if PostgresProposalRepository is not None:
        return PostgresProposalRepository
    module = importlib.import_module("src.infrastructure.proposals")
    return cast(ProposalRepositoryFactory, module.PostgresProposalRepository)


def build_repository() -> ProposalRepository:
    _ = proposal_store_backend_name()
    dsn = proposal_postgres_dsn()
    if not dsn:
        raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
    try:
        return cast(ProposalRepository, _postgres_repository_factory()(dsn=dsn))
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("PROPOSAL_POSTGRES_CONNECTION_FAILED") from exc
