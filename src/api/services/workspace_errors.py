from src.core.common.sensitive_error_details import contains_sensitive_error_detail

WORKSPACE_AI_UNAVAILABLE_DETAIL = "WORKSPACE_AI_UNAVAILABLE"
WORKSPACE_DRAFT_ACTION_INVALID_DETAIL = "WORKSPACE_DRAFT_ACTION_INVALID"
WORKSPACE_EVALUATION_UNAVAILABLE_DETAIL = "WORKSPACE_EVALUATION_UNAVAILABLE"
WORKSPACE_LIFECYCLE_HANDOFF_UNAVAILABLE_DETAIL = "WORKSPACE_LIFECYCLE_HANDOFF_UNAVAILABLE"


class WorkspaceEvaluationUnavailableError(Exception):
    pass


class WorkspaceSavedVersionNotFoundError(Exception):
    pass


class WorkspaceLifecycleHandoffUnavailableError(Exception):
    pass


def safe_workspace_error_detail(detail: str, *, fallback: str) -> str:
    if contains_sensitive_error_detail(detail):
        return fallback
    return detail
