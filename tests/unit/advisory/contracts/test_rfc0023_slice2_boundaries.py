import ast
from pathlib import Path

from src.api.main import app


def test_workspace_ai_service_delegates_evidence_building_to_core_workspace() -> None:
    tree = ast.parse(Path("src/api/services/workspace_ai_service.py").read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "src.core.workspace.assistant_evidence" in imported_modules
    assert "WorkspaceAssistantEvidence" not in {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }


def test_workspace_rationale_openapi_does_not_claim_proposal_narrative_support() -> None:
    openapi = app.openapi()
    operation = openapi["paths"]["/advisory/workspaces/{workspace_id}/assistant/rationale"]["post"]
    operation_text = " ".join(
        str(value)
        for value in (
            operation.get("summary"),
            operation.get("description"),
            operation.get("operationId"),
        )
    ).lower()

    assert "workspace rationale" in operation_text
    assert "proposal narrative" not in operation_text
    assert "client-ready" not in operation_text


def test_advisory_simulation_tag_does_not_claim_client_ready_artifacts() -> None:
    tag_descriptions = {
        tag["name"]: tag.get("description", "")
        for tag in app.openapi().get("tags", [])
        if isinstance(tag, dict)
    }

    simulation_description = tag_descriptions["Advisory Simulation"]
    assert "deterministic proposal evidence" in simulation_description
    assert "client-ready artifact" not in simulation_description
