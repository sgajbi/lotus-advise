import importlib
import inspect
from pathlib import Path

import pytest

import src.api.main as api_main
from src.api.openapi_tags import OPENAPI_TAGS
from src.api.proposals import (
    router as proposal_router,
)
from src.api.proposals import (
    routes_async,
    routes_delivery,
    routes_lifecycle,
    routes_memo,
    routes_policy_evaluations,
    routes_policy_packs,
    routes_support,
)
from src.api.proposals.errors import raise_proposal_http_exception
from src.api.routers.advisory_simulation import (
    build_proposal_artifact_endpoint,
    simulate_proposal,
)
from src.integrations.lotus_core.simulation import (
    LotusCoreSimulationUnavailableError,
    simulate_with_lotus_core,
)

workspace_router = importlib.import_module("src.api.workspaces.router")
advisory_simulation_router = importlib.import_module("src.api.routers.advisory_simulation")
integration_capabilities_router = importlib.import_module(
    "src.api.routers.integration_capabilities"
)
bank_demo_proof_router = importlib.import_module("src.api.routers.bank_demo_proof")
advisory_simulation_service = importlib.import_module(
    "src.api.services.advisory_simulation_service"
)
copilot_dependencies = importlib.import_module("src.api.proposals.copilot_dependencies")
workspace_ai_service = importlib.import_module("src.api.services.workspace_ai_service")
workspace_store = importlib.import_module("src.api.services.workspace_store")
workspace_service = importlib.import_module("src.api.services.workspace_service")

HTTP_EXCEPTION_ALLOWED_FILES = {
    Path("src/api/proposals/copilot_errors.py"),
    Path("src/api/proposals/errors.py"),
    Path("src/api/proposals/report_errors.py"),
    Path("src/api/proposals/runtime_errors.py"),
    Path("src/api/routers/bank_demo_proof_errors.py"),
    Path("src/api/routers/runtime_utils.py"),
    Path("src/api/services/advisory_simulation_errors.py"),
    Path("src/api/workspaces/errors.py"),
}


def test_raise_proposal_http_exception_re_raises_unknown_exception():
    with pytest.raises(ValueError, match="unexpected"):
        raise_proposal_http_exception(ValueError("unexpected"))


def test_lotus_core_simulation_raises_when_core_base_url_not_configured(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="LOTUS_CORE_SIMULATION_UNAVAILABLE",
    ):
        simulate_with_lotus_core(
            request=object(),  # type: ignore[arg-type]
            request_hash="hash",
            idempotency_key=None,
            correlation_id="corr-test",
        )


def test_lotus_core_simulation_does_not_use_query_base_url(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", "http://core-query.dev.lotus")

    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="LOTUS_CORE_SIMULATION_UNAVAILABLE",
    ):
        simulate_with_lotus_core(
            request=object(),  # type: ignore[arg-type]
            request_hash="hash",
            idempotency_key=None,
            correlation_id="corr-test",
        )


def test_advisory_simulation_routes_do_not_depend_on_legacy_db_session():
    for endpoint in (simulate_proposal, build_proposal_artifact_endpoint):
        assert "db" not in inspect.signature(endpoint).parameters


def test_api_main_does_not_export_legacy_proposal_idempotency_cache():
    assert not hasattr(api_main, "PROPOSAL_IDEMPOTENCY_CACHE")
    assert not hasattr(api_main, "MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE")
    assert "PROPOSAL_IDEMPOTENCY_CACHE" not in api_main.__all__
    assert "MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE" not in api_main.__all__


def test_api_main_does_not_export_router_or_engine_internals():
    stale_exports = {
        "_simulate_proposal_response",
        "build_proposal_artifact_endpoint",
        "run_proposal_simulation",
        "simulate_proposal",
    }

    assert stale_exports.isdisjoint(api_main.__all__)
    for export_name in stale_exports:
        assert not hasattr(api_main, export_name)


def test_deprecated_core_engine_shim_is_removed():
    assert not Path("src/core/engine.py").exists()


def test_api_main_uses_shared_openapi_tag_catalog():
    source = Path("src/api/main.py").read_text(encoding="utf-8")

    assert "from src.api.openapi_tags import OPENAPI_TAGS" in source
    assert "openapi_tags=OPENAPI_TAGS" in source
    assert api_main.app.openapi_tags == OPENAPI_TAGS


def test_api_main_uses_shared_problem_detail_builder():
    source = Path("src/api/main.py").read_text(encoding="utf-8")

    assert "from src.api.problem_details import build_problem_detail_response" in source
    assert "application/problem+json" not in source
    assert source.count("build_problem_detail_response(") == 3


def test_memo_routes_use_shared_response_metadata():
    source = inspect.getsource(routes_memo)

    assert "responses={" not in source
    assert "responses=MEMO_CREATE_RESPONSES" in source
    assert "responses=MEMO_REPORT_PACKAGE_RESPONSES" in source
    assert "responses=MEMO_AI_COMMENTARY_RESPONSES" in source
    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert "LotusReportUnavailableError" not in source
    assert "run_lotus_report_operation" in source
    assert source.count("run_proposal_operation(") == 9


def test_memo_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_memo.py").read_text(encoding="utf-8")

    assert "from fastapi import Depends, status" in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "Query(" not in source
    assert "ProposalIdPath" in source
    assert "ProposalMemoSourceVersionNoPath" in source
    assert "ProposalMemoCreateIdempotencyKeyHeader" in source
    assert "ProposalMemoReviewIdempotencyKeyHeader" in source
    assert "ProposalMemoAudienceQuery" in source


def test_policy_pack_routes_use_shared_response_metadata():
    source = inspect.getsource(routes_policy_packs)

    assert "responses={" not in source
    assert "responses=POLICY_PACK_LIST_RESPONSES" in source
    assert "responses=POLICY_PACK_VALIDATE_RESPONSES" in source
    assert "responses=POLICY_PACK_ACTIVATE_RESPONSES" in source
    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert 'AssertionError("unreachable")' not in source
    assert source.count("run_proposal_operation(") == 3


def test_policy_pack_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_policy_packs.py").read_text(encoding="utf-8")

    assert "from fastapi import status" in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "PolicyPackIdPath" in source
    assert "PolicyPackVersionPath" in source
    assert "PolicyPackValidationIdempotencyKeyHeader" in source
    assert "PolicyPackActivationIdempotencyKeyHeader" in source


def test_support_routes_use_shared_response_metadata():
    source = inspect.getsource(routes_support)

    assert "responses={" not in source
    assert "responses=SUPPORT_LINEAGE_RESPONSES" in source
    assert "responses=SUPPORT_VERSION_REPLAY_RESPONSES" in source
    assert "responses=SUPPORT_ASYNC_REPLAY_RESPONSES" in source
    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert source.count("run_proposal_operation(") == 6


def test_support_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_support.py").read_text(encoding="utf-8")

    assert "from fastapi import Depends, status" in source
    assert "Path(" not in source
    assert "ProposalIdPath" in source
    assert "ProposalVersionNoPath" in source
    assert "ProposalIdempotencyKeyPath" in source
    assert "ProposalAsyncOperationIdPath" in source


def test_lifecycle_routes_use_shared_response_metadata():
    source = inspect.getsource(routes_lifecycle)

    assert "responses={" not in source
    assert "responses=PROPOSAL_CREATE_RESPONSES" in source
    assert "responses=PROPOSAL_VERSION_CREATE_RESPONSES" in source
    assert "responses=PROPOSAL_NARRATIVE_REVIEW_RESPONSES" in source
    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert source.count("run_proposal_operation(") == 9


def test_lifecycle_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_lifecycle.py").read_text(encoding="utf-8")

    assert "from fastapi import Depends, status" in source
    assert "Query(" not in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "ProposalIdPath" in source
    assert "ProposalCreateIdempotencyKeyHeader" in source
    assert "ProposalVersionCorrelationIdHeader" in source
    assert "ProposalListLimitQuery" in source
    assert "ProposalOptionalNarrativeReviewIdempotencyKeyHeader" in source


def test_workspace_routes_use_shared_response_metadata():
    source = inspect.getsource(workspace_router)

    assert "responses={" not in source
    assert "responses=WORKSPACE_CREATE_RESPONSES" in source
    assert "responses=WORKSPACE_DRAFT_ACTION_RESPONSES" in source
    assert "responses=WORKSPACE_HANDOFF_RESPONSES" in source
    assert "_raise_saved_version_not_found" not in source
    assert "from src.api.services.workspace_errors import" not in source
    assert "WorkspaceEvaluationUnavailableError" not in source
    assert "WorkspaceSavedVersionNotFoundError" not in source
    assert "WorkspaceAssistantUnavailableError" not in source
    assert "WorkspaceLifecycleHandoffUnavailableError" not in source
    assert "run_workspace_operation" in source
    assert source.count("run_workspace_operation(") == 11
    assert "from src.api.services.workspace_service import (\n    WorkspaceEvaluation" not in source


def test_workspace_routes_use_shared_parameter_contracts():
    source = Path("src/api/workspaces/router.py").read_text(encoding="utf-8")

    assert "from fastapi import APIRouter, Depends, status" in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "WorkspaceIdPath" in source
    assert "WorkspaceVersionIdPath" in source
    assert "WorkspaceCreateCorrelationIdHeader" in source
    assert "WorkspaceHandoffIdempotencyKeyHeader" in source


def test_workspace_ai_service_uses_shared_workspace_exception_types():
    source = inspect.getsource(workspace_ai_service)

    assert "class WorkspaceAssistantUnavailableError" not in source
    assert "from src.api.services.workspace_errors import" in source
    assert "WorkspaceAssistantUnavailableError" in source
    assert "LotusAIRationaleUnavailableError" not in source
    assert "run_workspace_ai_operation" in source


def test_workspace_store_uses_shared_workspace_exception_types():
    source = inspect.getsource(workspace_store)

    assert "class WorkspaceNotFoundError" not in source
    assert "from src.api.services.workspace_errors import WorkspaceNotFoundError" in source


def test_workspace_store_tests_import_shared_not_found_error():
    source = Path("tests/unit/advisory/api/test_workspace_store.py").read_text()

    assert "from src.api.services.workspace_errors import WorkspaceNotFoundError" in source
    assert "from src.api.services.workspace_store import WorkspaceNotFoundError" not in source


def test_workspace_service_uses_consolidated_workspace_imports():
    source = inspect.getsource(workspace_service)

    assert "WorkspaceLifecycleHandoffUnavailableError as" not in source
    assert "from src.api.services.workspace_errors import" not in source
    assert "workspace_store" in source
    assert "from src.api.services.workspace_store import" not in source
    assert "from src.core.workspace.versions import" not in source
    assert "workspace_saved_versions" in source
    assert "WorkspaceDraftActionError" not in source
    assert "apply_workspace_draft_action_to_session" in source
    assert "evaluate_advisory_proposal" not in source
    assert "reevaluate_workspace_session_state" in source
    assert "build_initial_workspace_context" not in source
    assert "build_workspace_session(" not in source


def test_workspace_lifecycle_handoff_uses_shared_idempotency_helper():
    source = Path("src/api/services/workspace_lifecycle_handoff.py").read_text(encoding="utf-8")

    assert "normalize_required_idempotency_key" not in source
    assert "WORKSPACE_HANDOFF_IDEMPOTENCY_KEY_REQUIRED" not in source
    assert "normalize_workspace_handoff_idempotency_key" in source
    assert "WORKSPACE_LIFECYCLE_HANDOFF_UNAVAILABLE_DETAIL" not in source
    assert "WorkspaceHandoffError" not in source
    assert "run_workspace_handoff_operation" in source


def test_proposal_router_uses_shared_runtime_error_helpers():
    source = inspect.getsource(proposal_router)

    assert "HTTPException(" not in source
    assert "_backend_init_error_detail" not in source
    assert "assert_feature_enabled(" not in source
    assert "except RuntimeError as exc" not in source
    assert "proposal_backend_unavailable_exception" not in source
    assert "proposal_backend_connection_failed_exception" not in source
    assert "resolve_proposal_runtime_dependency" in source
    assert "assert_proposal_lifecycle_enabled" in source
    assert source.count("importlib.import_module(") == 1
    assert "_ROUTE_MODULES" in source


def test_advisory_copilot_routes_use_shared_error_boundary():
    source = Path("src/api/proposals/routes_advisory_copilot.py").read_text(encoding="utf-8")

    assert "except ValueError as exc" not in source
    assert source.count("run_copilot_operation(") == 7


def test_advisory_copilot_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_advisory_copilot.py").read_text(encoding="utf-8")

    assert "from fastapi import Depends, status" in source
    assert "Query(" not in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "AdvisoryCopilotCorrelationIdHeader" in source
    assert "AdvisoryCopilotOptionalIdempotencyKeyHeader" in source
    assert "AdvisoryCopilotReviewIdempotencyKeyHeader" in source
    assert "AdvisoryCopilotEvidencePacketIdPath" in source
    assert "AdvisoryCopilotRunLimitQuery" in source


def test_advisor_cockpit_routes_use_shared_error_boundary():
    source = Path("src/api/proposals/routes_advisor_cockpit.py").read_text(encoding="utf-8")

    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert source.count("run_proposal_operation(") == 4


def test_advisor_cockpit_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_advisor_cockpit.py").read_text(encoding="utf-8")

    assert "from fastapi import Depends, status" in source
    assert "Query(" not in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "AdvisorCockpitPortfolioIdQuery" in source
    assert "AdvisorCockpitCallerRoleQuery" in source
    assert "AdvisorCockpitCorrelationIdHeader" in source
    assert "AdvisorCockpitAcknowledgementIdempotencyKeyHeader" in source


def test_delivery_routes_use_shared_proposal_error_boundary():
    source = inspect.getsource(routes_delivery)

    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert "LotusReportUnavailableError" not in source
    assert "run_lotus_report_operation" in source
    assert source.count("run_proposal_operation(") == 6


def test_delivery_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_delivery.py").read_text(encoding="utf-8")

    assert "from fastapi import Depends, status" in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "ProposalIdPath" in source
    assert "ProposalExecutionHandoffIdempotencyKeyHeader" in source


def test_policy_evaluation_routes_use_shared_proposal_error_boundary():
    source = inspect.getsource(routes_policy_evaluations)

    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert "LotusReportUnavailableError" not in source
    assert "run_lotus_report_operation" in source
    assert source.count("run_proposal_operation(") == 10


def test_policy_evaluation_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_policy_evaluations.py").read_text(encoding="utf-8")

    assert "from fastapi import status" in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "Query(" not in source
    assert "PolicyEvaluationProposalIdPath" in source
    assert "PolicyEvaluationProposalVersionIdPath" in source
    assert "PolicyEvaluationFinalizeIdempotencyKeyHeader" in source
    assert "PolicyEvaluationIdPath" in source
    assert "PolicyEvaluationStatusQuery" in source


def test_async_routes_use_shared_proposal_error_boundary():
    source = inspect.getsource(routes_async)

    assert "raise_proposal_http_exception" not in source
    assert "ProposalNotFoundError" not in source
    assert source.count("run_proposal_operation(") == 4


def test_async_routes_use_shared_parameter_contracts():
    source = Path("src/api/proposals/routes_async.py").read_text(encoding="utf-8")

    assert "from fastapi import BackgroundTasks, Depends, status" in source
    assert "Header(" not in source
    assert "Path(" not in source
    assert "ProposalAsyncCreateIdempotencyKeyHeader" in source
    assert "ProposalAsyncCorrelationIdHeader" in source
    assert "ProposalAsyncOperationIdPath" in source
    assert "ProposalAsyncCorrelationIdPath" in source
    assert "ProposalIdPath" in source


def test_direct_http_exception_construction_stays_in_error_boundary_modules():
    offenders = []
    for path in Path("src/api").rglob("*.py"):
        normalized = Path(path.as_posix())
        source = path.read_text()
        if "HTTPException(" in source and normalized not in HTTP_EXCEPTION_ALLOWED_FILES:
            offenders.append(str(normalized))

    assert offenders == []


def test_copilot_dependencies_use_shared_repository_error_helper():
    source = inspect.getsource(copilot_dependencies)

    assert "HTTPException(" not in source
    assert "safe_copilot_repository_error_detail" not in source
    assert "copilot_repository_unavailable_exception" in source


def test_advisory_simulation_routes_use_shared_response_metadata():
    source = inspect.getsource(advisory_simulation_router)

    assert "responses={" not in source
    assert "responses=PROPOSAL_SIMULATION_RESPONSES" in source
    assert "responses=PROPOSAL_ARTIFACT_RESPONSES" in source


def test_advisory_simulation_routes_use_shared_parameter_contracts():
    source = Path("src/api/routers/advisory_simulation.py").read_text(encoding="utf-8")

    assert "from fastapi import APIRouter, status" in source
    assert "Header(" not in source
    assert "ProposalSimulationIdempotencyKeyHeader" in source
    assert "ProposalArtifactIdempotencyKeyHeader" in source
    assert "ProposalSimulationCorrelationIdHeader" in source
    assert "ProposalArtifactCorrelationIdHeader" in source


def test_advisory_simulation_service_uses_shared_error_helpers():
    source = inspect.getsource(advisory_simulation_service)

    assert "HTTPException(" not in source
    assert "normalize_required_idempotency_key" not in source
    assert "normalize_simulation_idempotency_key" in source
    assert "ProposalSimulationGateError" not in source
    assert "validate_simulation_request_enabled" in source
    assert "ProposalContextResolutionError" not in source
    assert "resolve_simulation_request" not in source
    assert "resolve_simulation_input_with_validation" in source
    assert "AlternativesRequestNormalizationError" not in source
    assert "evaluate_advisory_proposal" not in source
    assert "build_context_resolution_evidence" not in source
    assert "evaluate_simulation_result" in source
    assert "hash_canonical_payload" not in source
    assert "canonicalize_simulation_request_payload" not in source
    assert "build_simulation_request_hash" in source
    assert "datetime.now" not in source
    assert "ProposalSimulationIdempotencyRecord" not in source
    assert "get_replayed_simulation_result" in source
    assert "save_simulation_idempotency_result" in source


def test_integration_capabilities_routes_use_shared_response_metadata():
    source = inspect.getsource(integration_capabilities_router)

    assert "responses={" not in source
    assert "responses=INTEGRATION_CAPABILITIES_RESPONSES" in source


def test_integration_capabilities_routes_use_shared_parameter_contracts():
    source = Path("src/api/routers/integration_capabilities.py").read_text(encoding="utf-8")

    assert "from fastapi import APIRouter" in source
    assert "Query(" not in source
    assert "IntegrationConsumerSystemQuery" in source
    assert "IntegrationTenantIdQuery" in source


def test_capabilities_service_delegates_supportability_projection():
    source = Path("src/api/capabilities/service.py").read_text(encoding="utf-8")

    assert "from src.api.capabilities.supportability import build_advisory_supportability" in source
    assert "record_advisory_supportability" not in source
    assert "SupportabilityState" not in source
    assert "def build_advisory_supportability(" not in source


def test_capabilities_service_delegates_dependency_readiness_helpers():
    source = Path("src/api/capabilities/service.py").read_text(encoding="utf-8")

    assert "from src.api.capabilities.dependencies import" in source
    assert "def dependency_map(" not in source
    assert "def dependency_ready(" not in source
    assert "BANK_DEMO_PROOF_DEPENDENCY_KEYS" not in source


def test_bank_demo_proof_routes_use_shared_response_metadata():
    source = inspect.getsource(bank_demo_proof_router)

    assert "responses={" not in source
    assert "responses=BANK_DEMO_PROOF_PACK_RESPONSES" in source
    assert "_contains_sensitive_error_detail" not in source
    assert "HTTPException(" not in source
    assert "except ValueError as exc" not in source
    assert "run_bank_demo_proof_operation" in source


def test_bank_demo_proof_routes_use_shared_parameter_contracts():
    source = Path("src/api/routers/bank_demo_proof.py").read_text(encoding="utf-8")

    assert "from fastapi import APIRouter, status" in source
    assert "Header(" not in source
    assert "BankDemoProofCorrelationIdHeader" in source
