from src.core.models import ProposalSimulateRequest

PROPOSAL_SIMULATION_DISABLED_MESSAGE = (
    "PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true"
)


class ProposalSimulationGateError(ValueError):
    pass


def validate_proposal_simulation_enabled(
    *,
    request: ProposalSimulateRequest,
    require_simulation_flag: bool = True,
) -> None:
    if require_simulation_flag and not request.options.enable_proposal_simulation:
        raise ProposalSimulationGateError(PROPOSAL_SIMULATION_DISABLED_MESSAGE)
