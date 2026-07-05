import importlib
import os
from typing import Callable, cast

from src.core.policy_packs.repositories import (
    PolicyEvaluationRepository,
    PolicyPackCatalogRepository,
)
from src.runtime.proposal_repositories import (
    _postgres_connection_exception_types,
    proposal_postgres_dsn,
)

PolicyEvaluationRepositoryFactory = Callable[..., PolicyEvaluationRepository]
PolicyPackCatalogRepositoryFactory = Callable[..., PolicyPackCatalogRepository]

PostgresPolicyEvaluationRepository: PolicyEvaluationRepositoryFactory | None = None
PostgresPolicyPackCatalogRepository: PolicyPackCatalogRepositoryFactory | None = None


def policy_store_backend_name() -> str:
    backend = os.getenv("POLICY_STORE_BACKEND", "POSTGRES").strip().upper()
    if backend != "POSTGRES":
        raise RuntimeError("POLICY_STORE_BACKEND_UNSUPPORTED")
    return backend


def policy_postgres_dsn() -> str:
    return os.getenv("POLICY_POSTGRES_DSN", "").strip() or proposal_postgres_dsn()


def _postgres_policy_evaluation_repository_factory() -> PolicyEvaluationRepositoryFactory:
    if PostgresPolicyEvaluationRepository is not None:
        return PostgresPolicyEvaluationRepository
    module = importlib.import_module("src.infrastructure.policy_packs")
    return cast(
        PolicyEvaluationRepositoryFactory,
        module.PostgresPolicyEvaluationRepository,
    )


def _postgres_policy_pack_catalog_repository_factory() -> PolicyPackCatalogRepositoryFactory:
    if PostgresPolicyPackCatalogRepository is not None:
        return PostgresPolicyPackCatalogRepository
    module = importlib.import_module("src.infrastructure.policy_packs")
    return cast(
        PolicyPackCatalogRepositoryFactory,
        module.PostgresPolicyPackCatalogRepository,
    )


def build_policy_evaluation_repository() -> PolicyEvaluationRepository:
    _ = policy_store_backend_name()
    dsn = policy_postgres_dsn()
    if not dsn:
        raise RuntimeError("POLICY_POSTGRES_DSN_REQUIRED")
    try:
        return cast(
            PolicyEvaluationRepository,
            _postgres_policy_evaluation_repository_factory()(dsn=dsn),
        )
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("POLICY_POSTGRES_CONNECTION_FAILED") from exc


def build_policy_pack_catalog_repository() -> PolicyPackCatalogRepository:
    _ = policy_store_backend_name()
    dsn = policy_postgres_dsn()
    if not dsn:
        raise RuntimeError("POLICY_POSTGRES_DSN_REQUIRED")
    try:
        return cast(
            PolicyPackCatalogRepository,
            _postgres_policy_pack_catalog_repository_factory()(dsn=dsn),
        )
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("POLICY_POSTGRES_CONNECTION_FAILED") from exc
