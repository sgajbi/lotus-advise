from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Path, Query, status

from src.api.proposals import router as shared
from src.api.proposals.copilot_dependencies import (
    get_advisory_copilot_application_service,
    get_advisory_proposal_repository,
)
from src.api.proposals.copilot_errors import (
    ADVISORY_COPILOT_RESPONSES,
    raise_copilot_http_exception,
)
from src.core.advisory_copilot.api_models import (
    AdvisoryCopilotActionRequest,
    AdvisoryCopilotEvidencePacketCreateRequest,
    AdvisoryCopilotEvidencePacketResponse,
    AdvisoryCopilotProposalVersionEvidenceRequest,
    AdvisoryCopilotReviewRequest,
    AdvisoryCopilotReviewResponse,
    AdvisoryCopilotRunPage,
    AdvisoryCopilotRunResponse,
    AdvisoryCopilotSupportabilityResponse,
)
from src.core.advisory_copilot.application import (
    AdvisoryCopilotApplicationService,
    build_advisory_copilot_supportability_response,
)
from src.core.proposals.repository import ProposalRepository

_COPILOT_CORRELATION_ID_MAX_LENGTH = 128
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_IDEMPOTENCY_KEY_MAX_LENGTH = 128
_COPILOT_CURSOR_MAX_LENGTH = 512


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
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Correlation id for packet creation.",
            max_length=_COPILOT_CORRELATION_ID_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        return service.create_evidence_packet(
            payload=payload,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        raise_copilot_http_exception(exc)


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
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Correlation id for packet creation.",
            max_length=_COPILOT_CORRELATION_ID_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
    proposal_repository: ProposalRepository = Depends(get_advisory_proposal_repository),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        return service.create_proposal_version_evidence_packet(
            payload=payload,
            proposal_repository=proposal_repository,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        raise_copilot_http_exception(exc)


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
    evidence_packet_id: Annotated[
        str,
        Path(
            description="Copilot evidence-packet identifier.",
            min_length=1,
            max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        return service.get_evidence_packet(evidence_packet_id=evidence_packet_id)
    except ValueError as exc:
        raise_copilot_http_exception(exc)


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
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Replay-safe copilot action key.",
            max_length=_COPILOT_IDEMPOTENCY_KEY_MAX_LENGTH,
        ),
    ] = None,
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Correlation id for the copilot action.",
            max_length=_COPILOT_CORRELATION_ID_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunResponse:
    try:
        return service.run_action(
            payload=payload,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise_copilot_http_exception(exc)


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
    run_id: Annotated[
        str,
        Path(
            description="Advisory copilot run identifier.",
            min_length=1,
            max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunResponse:
    try:
        return service.get_run(run_id=run_id)
    except ValueError as exc:
        raise_copilot_http_exception(exc)


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
    run_id: Annotated[
        str,
        Path(
            description="Advisory copilot run identifier.",
            min_length=1,
            max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    payload: AdvisoryCopilotReviewRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Replay-safe review idempotency key.",
            min_length=1,
            max_length=_COPILOT_IDEMPOTENCY_KEY_MAX_LENGTH,
        ),
    ],
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Correlation id for the review action.",
            max_length=_COPILOT_CORRELATION_ID_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotReviewResponse:
    try:
        return service.review_run(
            run_id=run_id,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        raise_copilot_http_exception(exc)


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
    proposal_id: Annotated[
        str,
        Path(
            description="Proposal identifier.",
            min_length=1,
            max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    version_id: Annotated[
        str,
        Path(
            description="Proposal version identifier.",
            min_length=1,
            max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    limit: Annotated[
        int,
        Query(description="Bounded page size. Default is 25; maximum is 100.", ge=1, le=100),
    ] = 25,
    cursor: Annotated[
        str | None,
        Query(
            description="Opaque cursor from a previous copilot run page.",
            max_length=_COPILOT_CURSOR_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunPage:
    try:
        return service.list_proposal_version_runs(
            proposal_id=proposal_id,
            version_id=version_id,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise_copilot_http_exception(exc)
