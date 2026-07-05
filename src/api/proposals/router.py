import importlib
from typing import Optional, cast

from fastapi import APIRouter

from src.api.proposals import runtime
from src.api.proposals.feature_gates import (
    assert_proposal_async_operations_enabled,
    assert_proposal_lifecycle_enabled,
    assert_proposal_support_apis_enabled,
)
from src.api.proposals.runtime_errors import resolve_proposal_runtime_dependency
from src.api.runtime_flags import env_flag
from src.core.policy_packs import (
    configure_policy_evaluation_repository,
    configure_policy_pack_catalog_repository,
    reset_policy_evaluation_store_for_tests,
    reset_policy_pack_catalog_for_tests,
)
from src.core.policy_packs.application_service import PolicyEvidenceApplicationService
from src.core.policy_packs.repositories import (
    PolicyEvaluationRepository,
    PolicyPackCatalogRepository,
)
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.repository import ProposalRepository

router = APIRouter()

_REPOSITORY: Optional[ProposalRepository] = None
_SERVICE: Optional[ProposalWorkflowService] = None
_POLICY_EVALUATION_REPOSITORY: Optional[PolicyEvaluationRepository] = None
_POLICY_PACK_CATALOG_REPOSITORY: Optional[PolicyPackCatalogRepository] = None
_POLICY_EVIDENCE_SERVICE: Optional[PolicyEvidenceApplicationService] = None
_ROUTE_MODULES = (
    "src.api.proposals.routes_lifecycle",
    "src.api.proposals.routes_async",
    "src.api.proposals.routes_support",
    "src.api.proposals.routes_delivery",
    "src.api.proposals.routes_memo",
    "src.api.proposals.routes_policy_packs",
    "src.api.proposals.routes_policy_evaluations",
    "src.api.proposals.routes_advisor_cockpit",
    "src.api.proposals.routes_advisory_copilot",
    "src.api.proposals.routes_idea_intake",
)


def _proposal_store_backend_name() -> str:
    return cast(str, runtime.proposal_store_backend_name())


def _resolve_repository() -> ProposalRepository:
    global _REPOSITORY
    if _REPOSITORY is None:
        _REPOSITORY = runtime.build_repository()
    return cast(ProposalRepository, _REPOSITORY)


def get_proposal_workflow_service() -> ProposalWorkflowService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = resolve_proposal_runtime_dependency(
            lambda: ProposalWorkflowService(
                repository=_resolve_repository(),
                store_evidence_bundle=env_flag("PROPOSAL_STORE_EVIDENCE_BUNDLE", True),
                require_expected_state=env_flag("PROPOSAL_REQUIRE_EXPECTED_STATE", True),
                allow_portfolio_id_change_on_new_version=env_flag(
                    "PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION",
                    False,
                ),
                require_proposal_simulation_flag=env_flag("PROPOSAL_REQUIRE_SIMULATION_FLAG", True),
            )
        )
    return _SERVICE


def get_proposal_repository() -> ProposalRepository:
    return resolve_proposal_runtime_dependency(_resolve_repository)


def get_policy_evidence_application_service() -> PolicyEvidenceApplicationService:
    global _POLICY_EVIDENCE_SERVICE
    if _POLICY_EVIDENCE_SERVICE is None:
        _POLICY_EVIDENCE_SERVICE = PolicyEvidenceApplicationService()
    return _POLICY_EVIDENCE_SERVICE


def _resolve_policy_evaluation_repository() -> PolicyEvaluationRepository:
    global _POLICY_EVALUATION_REPOSITORY
    if _POLICY_EVALUATION_REPOSITORY is None:
        _POLICY_EVALUATION_REPOSITORY = runtime.build_policy_evaluation_repository()
        configure_policy_evaluation_repository(_POLICY_EVALUATION_REPOSITORY)
    return _POLICY_EVALUATION_REPOSITORY


def _resolve_policy_pack_catalog_repository() -> PolicyPackCatalogRepository:
    global _POLICY_PACK_CATALOG_REPOSITORY
    if _POLICY_PACK_CATALOG_REPOSITORY is None:
        _POLICY_PACK_CATALOG_REPOSITORY = runtime.build_policy_pack_catalog_repository()
        configure_policy_pack_catalog_repository(_POLICY_PACK_CATALOG_REPOSITORY)
    return _POLICY_PACK_CATALOG_REPOSITORY


def ensure_proposal_runtime_ready() -> None:
    _ = _resolve_repository()
    _ = _resolve_policy_pack_catalog_repository()
    _ = _resolve_policy_evaluation_repository()


def recover_proposal_async_runtime() -> int:
    return cast(int, get_proposal_workflow_service().recover_async_operations())


def reset_proposal_workflow_service_for_tests() -> None:
    global _REPOSITORY
    global _SERVICE
    global _POLICY_EVALUATION_REPOSITORY
    global _POLICY_PACK_CATALOG_REPOSITORY
    global _POLICY_EVIDENCE_SERVICE
    _REPOSITORY = None
    _SERVICE = None
    _POLICY_EVALUATION_REPOSITORY = None
    _POLICY_PACK_CATALOG_REPOSITORY = None
    _POLICY_EVIDENCE_SERVICE = None
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()


def _assert_lifecycle_enabled() -> None:
    assert_proposal_lifecycle_enabled()


def _assert_support_apis_enabled() -> None:
    assert_proposal_support_apis_enabled()


def _assert_async_operations_enabled() -> None:
    assert_proposal_async_operations_enabled()


for route_module in _ROUTE_MODULES:
    importlib.import_module(route_module)
