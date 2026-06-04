from src.core.proposals.repository import ProposalRepository
from src.runtime import proposal_repositories


def proposal_store_backend_name() -> str:
    return proposal_repositories.proposal_store_backend_name()


def proposal_postgres_dsn() -> str:
    return proposal_repositories.proposal_postgres_dsn()


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return proposal_repositories._postgres_connection_exception_types()


def build_repository() -> ProposalRepository:
    return proposal_repositories.build_repository()
