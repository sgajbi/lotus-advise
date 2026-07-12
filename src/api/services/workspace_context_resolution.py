from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.workspace.draft_models import WorkspaceDraftState
from src.core.workspace.input_models import WorkspaceResolvedContext
from src.core.workspace.session_models import WorkspaceSession, WorkspaceSessionCreateRequest
from src.infrastructure.workspace import LotusCoreWorkspaceSourceContextResolver

_SOURCE_CONTEXT_RESOLVER = LotusCoreWorkspaceSourceContextResolver()


def build_workspace_simulate_request(session: WorkspaceSession) -> ProposalSimulateRequest:
    return _SOURCE_CONTEXT_RESOLVER.build_simulate_request(session)


def build_initial_workspace_context(
    *,
    request: WorkspaceSessionCreateRequest,
    fallback_as_of: str,
) -> tuple[WorkspaceResolvedContext, WorkspaceDraftState]:
    return _SOURCE_CONTEXT_RESOLVER.build_initial_context(
        request=request,
        fallback_as_of=fallback_as_of,
    )
