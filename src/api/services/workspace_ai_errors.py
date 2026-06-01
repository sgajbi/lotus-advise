from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.api.services.workspace_errors import (
    WORKSPACE_AI_UNAVAILABLE_DETAIL,
    WorkspaceAssistantUnavailableError,
    safe_workspace_error_detail,
)
from src.integrations.lotus_ai import LotusAIRationaleUnavailableError

_WorkspaceAiOperationResult = TypeVar("_WorkspaceAiOperationResult")


def run_workspace_ai_operation(
    operation: Callable[[], _WorkspaceAiOperationResult],
) -> _WorkspaceAiOperationResult:
    try:
        return operation()
    except LotusAIRationaleUnavailableError as exc:
        raise WorkspaceAssistantUnavailableError(
            safe_workspace_error_detail(str(exc), fallback=WORKSPACE_AI_UNAVAILABLE_DETAIL)
        ) from exc
