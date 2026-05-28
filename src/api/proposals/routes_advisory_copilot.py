from __future__ import annotations

from typing import Annotated, NoReturn, cast

from fastapi import Depends, Header, HTTPException, Path, Query, status

from src.api.proposals import router as shared
from src.api.proposals.router import get_proposal_repository
from src.api.proposals.runtime import proposal_postgres_dsn
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
    AdvisoryCopilotDraftGenerator,
    build_advisory_copilot_supportability_response,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.policy_packs.persistence import list_policy_evaluation_records
from src.core.proposals.repository import ProposalRepository
from src.infrastructure.advisory_copilot import PostgresAdvisoryCopilotRepository
from src.integrations.lotus_ai import generate_advisory_copilot_draft_with_lotus_ai

ADVISORY_COPILOT_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {"description": "Copilot evidence packet or run was not found."},
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key or evidence-packet identifier conflicts with prior data."
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "Copilot request failed validation or guardrail-safe persistence checks."
    },
}

_COPILOT_REPOSITORY: AdvisoryCopilotRepository | None = None


def get_advisory_copilot_repository() -> AdvisoryCopilotRepository:
    global _COPILOT_REPOSITORY
    if _COPILOT_REPOSITORY is None:
        dsn = _advisory_copilot_postgres_dsn()
        try:
            _COPILOT_REPOSITORY = PostgresAdvisoryCopilotRepository(dsn=dsn)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
    return _COPILOT_REPOSITORY


def reset_advisory_copilot_repository_for_tests() -> None:
    global _COPILOT_REPOSITORY
    _COPILOT_REPOSITORY = None


def get_advisory_copilot_application_service(
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotApplicationService:
    return AdvisoryCopilotApplicationService(
        repository=repository,
        draft_generator=cast(
            AdvisoryCopilotDraftGenerator,
            generate_advisory_copilot_draft_with_lotus_ai,
        ),
        policy_evaluation_loader=list_policy_evaluation_records,
    )


@shared.router.post(
    "/advisory/copilot/evidence-packets",
    response_model=AdvisoryCopilotEvidencePacketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Advisory Copilot"],
    summary="Create Advisory Copilot Evidence Packet",
    description=(
        "Builds and persists a bounded, redacted evidence packet for a governed advisory "
        "copilot action. The endpoint stores source refs, packet hash, audience projection, "
        "unsupported-evidence posture, and audit context without accepting raw prompts."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def create_advisory_copilot_evidence_packet(
    payload: AdvisoryCopilotEvidencePacketCreateRequest,
    correlation_id: Annotated[
        str | None,
        Header(alias="X-Correlation-ID", description="Correlation id for packet creation."),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        return service.create_evidence_packet(
            payload=payload,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        _raise_copilot_http_exception(exc)


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
        Header(alias="X-Correlation-ID", description="Correlation id for packet creation."),
    ] = None,
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
    proposal_repository: ProposalRepository = Depends(get_proposal_repository),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        return service.create_proposal_version_evidence_packet(
            payload=payload,
            proposal_repository=proposal_repository,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        _raise_copilot_http_exception(exc)


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
    evidence_packet_id: Annotated[str, Path(description="Copilot evidence-packet identifier.")],
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        return service.get_evidence_packet(evidence_packet_id=evidence_packet_id)
    except ValueError as exc:
        _raise_copilot_http_exception(exc)


@shared.router.post(
    "/advisory/copilot/actions",
    response_model=AdvisoryCopilotRunResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="Run Governed Advisory Copilot Action",
    description=(
        "Executes a governed advisory copilot action from a persisted evidence packet through "
        "the approved lotus-ai workflow-pack seam, then persists review-gated output, hashes, "
        "guardrail posture, lineage, and audit context."
    ),
    responses=ADVISORY_COPILOT_RESPONSES,
)
def run_advisory_copilot_action(
    payload: AdvisoryCopilotActionRequest,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", description="Replay-safe copilot action key."),
    ] = None,
    correlation_id: Annotated[
        str | None,
        Header(alias="X-Correlation-ID", description="Correlation id for the copilot action."),
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
        _raise_copilot_http_exception(exc)


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
    run_id: Annotated[str, Path(description="Advisory copilot run identifier.")],
    service: AdvisoryCopilotApplicationService = Depends(get_advisory_copilot_application_service),
) -> AdvisoryCopilotRunResponse:
    try:
        return service.get_run(run_id=run_id)
    except ValueError as exc:
        _raise_copilot_http_exception(exc)


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
    run_id: Annotated[str, Path(description="Advisory copilot run identifier.")],
    payload: AdvisoryCopilotReviewRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", description="Replay-safe review idempotency key."),
    ],
    correlation_id: Annotated[
        str | None,
        Header(alias="X-Correlation-ID", description="Correlation id for the review action."),
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
        _raise_copilot_http_exception(exc)


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
    proposal_id: Annotated[str, Path(description="Proposal identifier.")],
    version_id: Annotated[str, Path(description="Proposal version identifier.")],
    limit: Annotated[
        int,
        Query(description="Bounded page size. Default is 25; maximum is 100.", ge=1, le=100),
    ] = 25,
    cursor: Annotated[
        str | None,
        Query(description="Opaque cursor from a previous copilot run page."),
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
        _raise_copilot_http_exception(exc)


def _advisory_copilot_postgres_dsn() -> str:
    import os

    return os.getenv("ADVISORY_COPILOT_POSTGRES_DSN", "").strip() or proposal_postgres_dsn()


def _raise_copilot_http_exception(exc: ValueError) -> NoReturn:
    detail = str(exc)
    if detail.endswith("_NOT_FOUND"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    if "CONFLICT" in detail or "TERMINAL" in detail:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc
