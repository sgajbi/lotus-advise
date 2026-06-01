import pytest
from fastapi import HTTPException

from src.api.services.workspace_errors import (
    WorkspaceAssistantUnavailableError,
    WorkspaceEvaluationUnavailableError,
    WorkspaceLifecycleHandoffUnavailableError,
    WorkspaceNotFoundError,
    WorkspaceSavedVersionNotFoundError,
)
from src.api.workspaces.errors import run_workspace_operation


def test_run_workspace_operation_returns_successful_result() -> None:
    assert run_workspace_operation(lambda: {"workspace_id": "aws_001"}) == {
        "workspace_id": "aws_001"
    }


@pytest.mark.parametrize(
    "exc",
    [
        WorkspaceNotFoundError("WORKSPACE_NOT_FOUND"),
        WorkspaceSavedVersionNotFoundError("WORKSPACE_SAVED_VERSION_NOT_FOUND"),
    ],
)
def test_run_workspace_operation_maps_not_found_errors(exc: Exception) -> None:
    with pytest.raises(HTTPException) as exc_info:
        run_workspace_operation(lambda: (_ for _ in ()).throw(exc))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == str(exc)


@pytest.mark.parametrize(
    "exc",
    [
        WorkspaceEvaluationUnavailableError("WORKSPACE_EVALUATION_UNAVAILABLE"),
        WorkspaceLifecycleHandoffUnavailableError("WORKSPACE_HANDOFF_UNAVAILABLE"),
    ],
)
def test_run_workspace_operation_maps_conflict_errors(exc: Exception) -> None:
    with pytest.raises(HTTPException) as exc_info:
        run_workspace_operation(lambda: (_ for _ in ()).throw(exc))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == str(exc)


def test_run_workspace_operation_maps_lotus_ai_rationale_unavailable_to_503() -> None:
    with pytest.raises(HTTPException) as exc_info:
        run_workspace_operation(
            lambda: (_ for _ in ()).throw(
                WorkspaceAssistantUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")
            )
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "LOTUS_AI_RATIONALE_UNAVAILABLE"


def test_run_workspace_operation_maps_workspace_ai_unavailable_to_conflict() -> None:
    with pytest.raises(HTTPException) as exc_info:
        run_workspace_operation(
            lambda: (_ for _ in ()).throw(
                WorkspaceAssistantUnavailableError("WORKSPACE_AI_REQUIRES_EVALUATED_WORKSPACE")
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "WORKSPACE_AI_REQUIRES_EVALUATED_WORKSPACE"
