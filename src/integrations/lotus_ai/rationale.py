import sys
from typing import cast

from src.core.workspace.models import (
    WorkspaceAssistantEvidence,
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
)


class LotusAIRationaleUnavailableError(Exception):
    pass


def generate_workspace_rationale_with_lotus_ai(
    *,
    request: WorkspaceAssistantRequest,
    evidence: WorkspaceAssistantEvidence,
) -> WorkspaceAssistantResponse:
    main_module = sys.modules.get("src.api.main")
    if main_module is None:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")

    override = getattr(main_module, "generate_workspace_rationale_with_lotus_ai", None)
    if override is None:
        raise LotusAIRationaleUnavailableError("LOTUS_AI_RATIONALE_UNAVAILABLE")

    response = override(request=request, evidence=evidence)
    return cast(WorkspaceAssistantResponse, WorkspaceAssistantResponse.model_validate(response))
