from src.core.policy_packs.repositories import (
    PolicyEvaluationRepository,
    PolicyPackCatalogRepository,
)
from src.core.proposals.repository import ProposalRepository
from src.runtime import policy_repositories, proposal_repositories


def proposal_store_backend_name() -> str:
    return proposal_repositories.proposal_store_backend_name()


def proposal_postgres_dsn() -> str:
    return proposal_repositories.proposal_postgres_dsn()


def policy_store_backend_name() -> str:
    return policy_repositories.policy_store_backend_name()


def policy_postgres_dsn() -> str:
    return policy_repositories.policy_postgres_dsn()


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return proposal_repositories._postgres_connection_exception_types()


def build_repository() -> ProposalRepository:
    return proposal_repositories.build_repository()


def build_policy_evaluation_repository() -> PolicyEvaluationRepository:
    return policy_repositories.build_policy_evaluation_repository()


def build_policy_pack_catalog_repository() -> PolicyPackCatalogRepository:
    return policy_repositories.build_policy_pack_catalog_repository()
