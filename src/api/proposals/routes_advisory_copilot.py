from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Path, status

from src.api.proposals import router as shared
from src.api.proposals.runtime import proposal_postgres_dsn
from src.core.advisory_copilot import (
    build_copilot_evidence_packet,
    list_advisory_copilot_reviews,
    list_copilot_action_definitions,
    load_advisory_copilot_evidence_packet,
    persist_advisory_copilot_run,
    record_advisory_copilot_review,
    save_advisory_copilot_evidence_packet,
)
from src.core.advisory_copilot.api_models import (
    AdvisoryCopilotActionRequest,
    AdvisoryCopilotEvidencePacketCreateRequest,
    AdvisoryCopilotEvidencePacketResponse,
    AdvisoryCopilotReviewRequest,
    AdvisoryCopilotReviewResponse,
    AdvisoryCopilotRunPage,
    AdvisoryCopilotRunResponse,
    AdvisoryCopilotSupportabilityResponse,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
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
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotEvidencePacketResponse:
    try:
        packet = build_copilot_evidence_packet(
            evidence_packet_id=payload.evidence_packet_id,
            action_family=payload.action_family,
            portfolio_id=payload.portfolio_id,
            proposal_id=payload.proposal_id,
            audience=payload.audience,
            source_sections=payload.source_sections,
        )
        record = save_advisory_copilot_evidence_packet(
            repository=repository,
            evidence_packet=packet,
            audience=payload.audience,
            created_by=payload.created_by,
            reason=payload.reason,
            correlation_id=correlation_id or f"corr-{payload.evidence_packet_id}",
        )
        return AdvisoryCopilotEvidencePacketResponse(evidence_packet=packet, record=record)
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
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotEvidencePacketResponse:
    record = repository.get_evidence_packet(evidence_packet_id=evidence_packet_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="COPILOT_EVIDENCE_PACKET_NOT_FOUND",
        )
    packet = load_advisory_copilot_evidence_packet(
        repository=repository,
        evidence_packet_id=evidence_packet_id,
    )
    return AdvisoryCopilotEvidencePacketResponse(evidence_packet=packet, record=record)


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
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotRunResponse:
    try:
        evidence_packet = load_advisory_copilot_evidence_packet(
            repository=repository,
            evidence_packet_id=payload.evidence_packet_id,
        )
        draft = generate_advisory_copilot_draft_with_lotus_ai(
            evidence_packet=evidence_packet,
            audience=payload.audience,
            requested_outputs=list(payload.requested_outputs),
            requested_by=payload.requested_by,
            reason=payload.reason,
            requested_intents=payload.requested_intents,
            user_instruction=payload.user_instruction,
        )
        result = persist_advisory_copilot_run(
            repository=repository,
            evidence_packet=evidence_packet,
            audience=payload.audience,
            requested_outputs=payload.requested_outputs,
            requested_by=payload.requested_by,
            reason=payload.reason,
            draft_status=draft.status,
            output_sections=draft.sections,
            lineage=draft.lineage,
            review_guidance=draft.review_guidance,
            guardrail_reasons=cast(tuple[str, ...], draft.guardrail_reasons),
            correlation_id=correlation_id or f"corr-{payload.evidence_packet_id}",
            idempotency_key=idempotency_key,
            requested_intents=payload.requested_intents,
            user_instruction=payload.user_instruction,
        )
        return AdvisoryCopilotRunResponse(run=result.run, replayed=result.replayed)
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
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotRunResponse:
    run = repository.get_run(run_id=run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="COPILOT_RUN_NOT_FOUND")
    reviews = list_advisory_copilot_reviews(repository=repository, run_id=run_id)
    return AdvisoryCopilotRunResponse(run=run, reviews=reviews)


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
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotReviewResponse:
    try:
        result = record_advisory_copilot_review(
            repository=repository,
            run_id=run_id,
            action=payload.action,
            actor_id=payload.actor_id,
            reason=payload.reason,
            correlation_id=correlation_id or f"corr-{run_id}",
            idempotency_key=idempotency_key,
        )
        return AdvisoryCopilotReviewResponse(
            run=result.run,
            review=result.review,
            replayed=result.replayed,
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
    return AdvisoryCopilotSupportabilityResponse(
        support_status="ADVISE_API_CERTIFIED_GATEWAY_WORKBENCH_PENDING",
        client_ready_publication="BLOCKED",
        supported_action_families=tuple(
            definition.action_family for definition in list_copilot_action_definitions()
        ),
        boundaries=(
            "No client-ready publication",
            "No policy approval or sign-off authority",
            "No order, fill, settlement, or OMS authority",
            "Gateway and Workbench support remain pending later RFC-0027 slices",
        ),
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs",
    response_model=AdvisoryCopilotRunPage,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Copilot"],
    summary="List Proposal Version Copilot Runs",
    description="Lists persisted advisory copilot runs for a proposal version scope.",
    responses=ADVISORY_COPILOT_RESPONSES,
)
def list_proposal_version_copilot_runs(
    proposal_id: Annotated[str, Path(description="Proposal identifier.")],
    version_id: Annotated[str, Path(description="Proposal version identifier.")],
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotRunPage:
    runs = repository.list_runs_for_proposal_version(
        proposal_id=proposal_id,
        proposal_version_id=version_id,
        proposal_version_no=None,
    )
    return AdvisoryCopilotRunPage(items=tuple(runs), next_cursor=None)


def _advisory_copilot_postgres_dsn() -> str:
    import os

    return os.getenv("ADVISORY_COPILOT_POSTGRES_DSN", "").strip() or proposal_postgres_dsn()


def _raise_copilot_http_exception(exc: ValueError) -> None:
    detail = str(exc)
    if detail.endswith("_NOT_FOUND"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    if "CONFLICT" in detail or "TERMINAL" in detail:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc
