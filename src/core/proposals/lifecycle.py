from src.core.proposals.models import ProposalLifecycleOrigin


class ProposalLifecycleOriginError(ValueError):
    pass


def validate_lifecycle_origin(
    *,
    lifecycle_origin: ProposalLifecycleOrigin,
    source_workspace_id: str | None,
) -> None:
    if lifecycle_origin == "WORKSPACE_HANDOFF" and not source_workspace_id:
        raise ProposalLifecycleOriginError("WORKSPACE_HANDOFF_SOURCE_WORKSPACE_ID_REQUIRED")
    if lifecycle_origin == "DIRECT_CREATE" and source_workspace_id is not None:
        raise ProposalLifecycleOriginError("DIRECT_CREATE_CANNOT_INCLUDE_SOURCE_WORKSPACE_ID")
