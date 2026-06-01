from __future__ import annotations

from typing import cast

from src.api.services.workspace_errors import WorkspaceLifecycleHandoffUnavailableError
from src.core.common.idempotency import normalize_required_idempotency_key


def normalize_workspace_handoff_idempotency_key(idempotency_key: str | None) -> str:
    try:
        return cast(str, normalize_required_idempotency_key(idempotency_key))
    except ValueError as exc:
        raise WorkspaceLifecycleHandoffUnavailableError(
            "WORKSPACE_HANDOFF_IDEMPOTENCY_KEY_REQUIRED"
        ) from exc
