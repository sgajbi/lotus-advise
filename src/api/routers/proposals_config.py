import os

from src.infrastructure.proposals import InMemoryProposalRepository, PostgresProposalRepository


def proposal_store_backend_name() -> str:
    backend = os.getenv("PROPOSAL_STORE_BACKEND", "IN_MEMORY").strip().upper()
    if backend == "POSTGRES":
        return "POSTGRES"
    return "IN_MEMORY"


def proposal_postgres_dsn() -> str:
    return os.getenv("PROPOSAL_POSTGRES_DSN", "").strip()


def build_repository():
    backend = proposal_store_backend_name()
    if backend == "POSTGRES":
        dsn = proposal_postgres_dsn()
        if not dsn:
            raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
        try:
            return PostgresProposalRepository(dsn=dsn)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("PROPOSAL_POSTGRES_CONNECTION_FAILED") from exc
    return InMemoryProposalRepository()
