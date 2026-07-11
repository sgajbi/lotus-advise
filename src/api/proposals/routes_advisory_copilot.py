from __future__ import annotations

from typing import cast

from fastapi import Depends, status

from src.api.proposals import router as shared
from src.api.proposals.copilot_dependencies import (
    get_advisory_copilot_application_service,
    get_advisory_proposal_repository,
)
from src.api.proposals.copilot_errors import (
    ADVISORY_COPILOT_RESPONSES,
    ADVISORY_COPILOT_SUPPORTABILITY_RESPONSES,
    run_copilot_operation,
)
from src.api.proposals.copilot_parameters import (
    AdvisoryCopilotCorrelationIdHeader,
    AdvisoryCopilotEvidencePacketIdPath,
    AdvisoryCopilotOptionalIdempotencyKeyHeader,
    AdvisoryCopilotProposalIdPath,
    AdvisoryCopilotProposalVersionIdPath,
    AdvisoryCopilotReviewIdempotencyKeyHeader,
    AdvisoryCopilotRunCursorQuery,
    AdvisoryCopilotRunIdPath,
    AdvisoryCopilotRunLimitQuery,
)
from src.core.advisory_copilot.api_request_models import (
    AdvisoryCopilotActionRequest,
    AdvisoryCopilotEvidencePacketCreateRequest,
    AdvisoryCopilotProposalVersionEvidenceRequest,
    AdvisoryCopilotReviewRequest,
)
from src.core.advisory_copilot.api_response_models import (
    AdvisoryCopilotEvidencePacketResponse,
    AdvisoryCopilotReviewResponse,
    AdvisoryCopilotRunPage,
    AdvisoryCopilotRunResponse,
    AdvisoryCopilotSupportabilityResponse,
)
from src.core.advisory_copilot.application import (
    AdvisoryCopilotApplicationService,
)
from src.core.advisory_copilot.supportability import (
    build_advisory_copilot_supportability_response,
)
from src.core.proposals.repository import ProposalRepository


@shared.router.post(
    "/advisory/copilot/evidence-packets",
    response_model=AdvisoryCopilotEvidencePacketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Advisory Copilot"],
    summary="Create Advisory Copilot Evidence Packet",
    description=(
        "Builds and persists a bounded, redacted evidence packet for a governed advisory "
        "copilot action. The endpoint stores source refs, packet hash, audience projection, "
        "unsupported-evidence posture, and audit context without accepting unredacted AI inputs."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def create_advisory_copilot_evidence_packet(
    payload: AdvisoryCopilotEvidencePacketCreateRequest,
    correlation_id: AdvisoryCopilotCorrelationIdHeader = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotEvidencePacketResponse:
    return cast(
        AdvisoryCopilotEvidencePacketResponse,
        run_copilot_operation(
            lambda: service.create_evidence_packet(
                payload=payload,
                correlation_id=correlation_id,
            )
        ),
    )


@shared.router.post(
    "/advisory/copilot/evidence-packets/from-proposal-version",
    response_model=AdvisoryCopilotEvidencePacketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Advisory Copilot"],
    summary="Create Proposal Version Advisory Copilot Evidence Packet",
    description=(
        "Builds and persists a bounded advisory copilot evidence packet from Advise-owned "
        "proposal, memo, policy evaluation, advisor cockpit, report-readiness, and handoff "
        "records. This endpoint is the Workbench-safe projection path: callers request a "
        "proposal/version/action family, while Advise owns evidence selection, unsupported "
        "evidence, source refs, redaction, hashes, and lineage."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def create_advisory_copilot_evidence_packet_from_proposal_version(
    payload: AdvisoryCopilotProposalVersionEvidenceRequest,
    correlation_id: AdvisoryCopilotCorrelationIdHeader = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
    proposal_repository: ProposalRepository = Depends(get_advisory_proposal_repository),
) -> AdvisoryCopilotEvidencePacketResponse:
    return cast(
        AdvisoryCopilotEvidencePacketResponse,
        run_copilot_operation(
            lambda: service.create_proposal_version_evidence_packet(
                payload=payload,
                proposal_repository=proposal_repository,
                correlation_id=correlation_id,
            )
        ),
    )


@shared.router.get(
    "/advisory/copilot/evidence-packets/{evidence_packet_id}",
    response_model=AdvisoryCopilotEvidencePacketResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="Get Advisory Copilot Evidence Packet",
    description="Returns a persisted bounded copilot evidence packet and its audit context.",
    responses=ADVISORY_COPILOT_RESPONSES,
)
def get_advisory_copilot_evidence_packet(
    evidence_packet_id: AdvisoryCopilotEvidencePacketIdPath,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotEvidencePacketResponse:
    return cast(
        AdvisoryCopilotEvidencePacketResponse,
        run_copilot_operation(
            lambda: service.get_evidence_packet(evidence_packet_id=evidence_packet_id)
        ),
    )


@shared.router.post(
    "/advisory/copilot/actions",
    response_model=AdvisoryCopilotRunResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="Run Governed Advisory Copilot Action",
    description=(
        "Executes a governed advisory copilot action from a persisted evidence packet through "
        "the approved lotus-ai workflow-pack boundary, then persists review-gated output, hashes, "
        "guardrail posture, lineage, and audit context."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def run_advisory_copilot_action(
    payload: AdvisoryCopilotActionRequest,
    idempotency_key: AdvisoryCopilotOptionalIdempotencyKeyHeader = None,
    correlation_id: AdvisoryCopilotCorrelationIdHeader = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunResponse:
    return cast(
        AdvisoryCopilotRunResponse,
        run_copilot_operation(
            lambda: service.run_action(
                payload=payload,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
            )
        ),
    )


@shared.router.get(
    "/advisory/copilot/actions/{run_id}",
    response_model=AdvisoryCopilotRunResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="Get Advisory Copilot Run",
    description="Returns a persisted advisory copilot run with ordered review audit events.",
    responses=ADVISORY_COPILOT_RESPONSES,
)
def get_advisory_copilot_run(
    run_id: AdvisoryCopilotRunIdPath,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunResponse:
    return cast(
        AdvisoryCopilotRunResponse,
        run_copilot_operation(lambda: service.get_run(run_id=run_id)),
    )


@shared.router.post(
    "/advisory/copilot/actions/{run_id}/reviews",
    response_model=AdvisoryCopilotReviewResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="Review Advisory Copilot Run",
    description=(
        "Records an idempotent human review action for an advisory copilot run. Review approval "
        "is for internal use only and never approves proposals, policy outcomes, orders, reports, "
        "or client-ready communication."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def review_advisory_copilot_run(
    run_id: AdvisoryCopilotRunIdPath,
    payload: AdvisoryCopilotReviewRequest,
    idempotency_key: AdvisoryCopilotReviewIdempotencyKeyHeader,
    correlation_id: AdvisoryCopilotCorrelationIdHeader = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotReviewResponse:
    return cast(
        AdvisoryCopilotReviewResponse,
        run_copilot_operation(
            lambda: service.review_run(
                run_id=run_id,
                payload=payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        ),
    )


@shared.router.get(
    "/advisory/copilot/supportability",
    response_model=AdvisoryCopilotSupportabilityResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="Get Advisory Copilot Supportability",
    description=(
        "Returns the current Advise-owned advisory copilot API supportability posture and "
        "explicit unsupported claim boundaries."
    ),
    responses=ADVISORY_COPILOT_SUPPORTABILITY_RESPONSES,
)
def get_advisory_copilot_supportability() -> AdvisoryCopilotSupportabilityResponse:
    return build_advisory_copilot_supportability_response()


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs",
    response_model=AdvisoryCopilotRunPage,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="List Proposal Version Copilot Runs",
    description=(
        "Lists persisted advisory copilot runs for a proposal version scope using bounded "
        "keyset pagination. The list is ordered by newest run first and filtered in Advise so "
        "Gateway and Workbench can consume run history without rebuilding copilot lineage."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def list_proposal_version_copilot_runs(
    proposal_id: AdvisoryCopilotProposalIdPath,
    version_id: AdvisoryCopilotProposalVersionIdPath,
    limit: AdvisoryCopilotRunLimitQuery = 25,
    cursor: AdvisoryCopilotRunCursorQuery = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunPage:
    return cast(
        AdvisoryCopilotRunPage,
        run_copilot_operation(
            lambda: service.list_proposal_version_runs(
                proposal_id=proposal_id,
                version_id=version_id,
                limit=limit,
                cursor=cursor,
            )
        ),
    )
