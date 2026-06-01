from fastapi import APIRouter, status

from src.api.routers.advisory_simulation_parameters import (
    ProposalArtifactCorrelationIdHeader,
    ProposalArtifactIdempotencyKeyHeader,
    ProposalSimulationCorrelationIdHeader,
    ProposalSimulationIdempotencyKeyHeader,
)
from src.api.routers.advisory_simulation_responses import (
    PROPOSAL_ARTIFACT_RESPONSES,
    PROPOSAL_SIMULATION_RESPONSES,
)
from src.api.services import advisory_simulation_service as service
from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory.artifact_models import ProposalArtifact
from src.core.proposal_result_models import ProposalResult
from src.core.proposals import ProposalSimulationRequest

router = APIRouter()


@router.post(
    "/advisory/proposals/simulate",
    response_model=ProposalResult,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Simulation"],
    summary="Simulate an Advisory Proposal",
    description=(
        "Runs deterministic advisory proposal simulation from either a legacy direct payload or "
        "the normalized `stateless`/`stateful` advisory context contract.\\n\\n"
        "Normalized modes:\\n"
        "1) `stateless_input` for direct request-supplied simulation payloads\\n"
        "2) `stateful_input` for authoritative Lotus Core context resolution\\n\\n"
        "Legacy mode:\\n"
        "1) omit `input_mode` and send the direct simulation payload under `simulate_request` or "
        "as the historical top-level body shape\\n\\n"
        "Processing order:\\n"
        "1) Cash flows (if `proposal_apply_cash_flows_first=true`)\\n"
        "2) Manual security sells (instrument ascending)\\n"
        "3) Manual security buys (instrument ascending)\\n\\n"
        "Required header: `Idempotency-Key`.\\n"
        "Optional header: `X-Correlation-Id` (auto-generated when omitted).\\n\\n"
        "Requires `options.enable_proposal_simulation=true`."
    ),
    responses=PROPOSAL_SIMULATION_RESPONSES,
)
def simulate_proposal(
    request: ProposalSimulationRequest,
    idempotency_key: ProposalSimulationIdempotencyKeyHeader,
    correlation_id: ProposalSimulationCorrelationIdHeader = None,
) -> ProposalResult:
    return service.simulate_proposal_response(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )


@router.post(
    "/advisory/proposals/artifact",
    response_model=ProposalArtifact,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Simulation"],
    summary="Build Advisory Proposal Artifact",
    description=(
        "Runs advisory proposal simulation from the same normalized `stateless`/`stateful` "
        "contract used by lifecycle flows and returns a deterministic proposal artifact "
        "package. Legacy direct simulation payloads remain supported.\\n\\n"
        "Required header: `Idempotency-Key`.\\n"
        "Optional header: `X-Correlation-Id` (auto-generated when omitted).\\n\\n"
        "Requires `options.enable_proposal_simulation=true`."
    ),
    responses=PROPOSAL_ARTIFACT_RESPONSES,
)
def build_proposal_artifact_endpoint(
    request: ProposalSimulationRequest,
    idempotency_key: ProposalArtifactIdempotencyKeyHeader,
    correlation_id: ProposalArtifactCorrelationIdHeader = None,
) -> ProposalArtifact:
    resolved_request = service.resolve_simulation_input(request)
    proposal_result = service.simulate_proposal_response(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        resolved_request=resolved_request,
    )
    return build_proposal_artifact(
        request=resolved_request.simulate_request,
        proposal_result=proposal_result,
    )
