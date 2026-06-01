from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status

from src.api.sensitive_error_details import contains_sensitive_error_detail
from src.api.services.workspace_errors import (
    WorkspaceAssistantUnavailableError,
    WorkspaceEvaluationUnavailableError,
    WorkspaceLifecycleHandoffUnavailableError,
    WorkspaceNotFoundError,
    WorkspaceSavedVersionNotFoundError,
)

WORKSPACE_ASSISTANT_UNAVAILABLE_DETAIL = "WORKSPACE_ASSISTANT_UNAVAILABLE"
WORKSPACE_CONFLICT_DETAIL = "WORKSPACE_CONFLICT"
WORKSPACE_NOT_FOUND_DETAIL = "WORKSPACE_NOT_FOUND"

LOTUS_AI_RATIONALE_UNAVAILABLE_DETAIL = "LOTUS_AI_RATIONALE_UNAVAILABLE"
T = TypeVar("T")


def safe_workspace_error_detail(error_detail: str, *, redacted_detail: str) -> str:
    if contains_sensitive_error_detail(error_detail):
        return redacted_detail
    return error_detail


def workspace_not_found_exception(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=safe_workspace_error_detail(
            str(exc),
            redacted_detail=WORKSPACE_NOT_FOUND_DETAIL,
        ),
    )


def workspace_conflict_exception(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=safe_workspace_error_detail(
            str(exc),
            redacted_detail=WORKSPACE_CONFLICT_DETAIL,
        ),
    )


def workspace_assistant_unavailable_exception(exc: Exception) -> HTTPException:
    detail = safe_workspace_error_detail(
        str(exc),
        redacted_detail=WORKSPACE_ASSISTANT_UNAVAILABLE_DETAIL,
    )
    if detail == LOTUS_AI_RATIONALE_UNAVAILABLE_DETAIL:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def run_workspace_operation(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except (WorkspaceNotFoundError, WorkspaceSavedVersionNotFoundError) as exc:
        raise workspace_not_found_exception(exc) from exc
    except (WorkspaceEvaluationUnavailableError, WorkspaceLifecycleHandoffUnavailableError) as exc:
        raise workspace_conflict_exception(exc) from exc
    except WorkspaceAssistantUnavailableError as exc:
        raise workspace_assistant_unavailable_exception(exc) from exc
