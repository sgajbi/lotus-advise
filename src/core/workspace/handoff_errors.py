from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.core.workspace.errors import (
    WORKSPACE_LIFECYCLE_HANDOFF_UNAVAILABLE_DETAIL,
    WorkspaceEvaluationUnavailableError,
    WorkspaceLifecycleHandoffUnavailableError,
    safe_workspace_error_detail,
)
from src.core.workspace.handoff import WorkspaceHandoffError

_WorkspaceHandoffOperationResult = TypeVar("_WorkspaceHandoffOperationResult")


def run_workspace_handoff_operation(
    operation: Callable[[], _WorkspaceHandoffOperationResult],
) -> _WorkspaceHandoffOperationResult:
    try:
        return operation()
    except (ValueError, WorkspaceEvaluationUnavailableError, WorkspaceHandoffError) as exc:
        raise WorkspaceLifecycleHandoffUnavailableError(
            safe_workspace_error_detail(
                str(exc),
                fallback=WORKSPACE_LIFECYCLE_HANDOFF_UNAVAILABLE_DETAIL,
            )
        ) from exc
