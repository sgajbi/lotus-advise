from typing import cast

import src.api.proposals.router as proposal_shared
from src.core.workspace.application import WorkspaceApplicationService
from src.core.workspace.ports import WorkspaceProposalLifecyclePort
from src.runtime.workspace_application import get_workspace_application_service


def get_workspace_application_service_dependency() -> WorkspaceApplicationService:
    return get_workspace_application_service()


def get_workspace_proposal_lifecycle_port() -> WorkspaceProposalLifecyclePort:
    proposal_shared._assert_lifecycle_enabled()
    return cast(
        WorkspaceProposalLifecyclePort,
        proposal_shared.get_proposal_workflow_service(),
    )
