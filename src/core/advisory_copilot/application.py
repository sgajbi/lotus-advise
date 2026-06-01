from __future__ import annotations

from typing import Any, Protocol, Sequence, cast

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
from src.core.advisory_copilot.correlation import resolve_advisory_copilot_correlation_id
from src.core.advisory_copilot.evidence_packets import build_copilot_evidence_packet
from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.packet_persistence import (
    load_advisory_copilot_evidence_packet,
    save_advisory_copilot_evidence_packet,
)
from src.core.advisory_copilot.pagination import normalize_copilot_run_page_size
from src.core.advisory_copilot.proposal_projection_persistence import (
    save_proposal_version_advisory_copilot_evidence_packet,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.request_hashing import build_advisory_copilot_run_request_hash
from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.advisory_copilot.review_persistence import (
    list_advisory_copilot_reviews,
    record_advisory_copilot_review,
)
from src.core.advisory_copilot.run_persistence import persist_advisory_copilot_run
from src.core.advisory_copilot.run_replay_policy import resolve_advisory_copilot_run_replay
from src.core.advisory_copilot.supportability import (
    build_advisory_copilot_supportability_response,
)
from src.core.advisory_copilot.type_models import CopilotAudience
from src.core.common.idempotency import (
    normalize_optional_idempotency_key,
    normalize_required_idempotency_key,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.repository import ProposalRepository


class AdvisoryCopilotDraft(Protocol):
    status: str
    sections: tuple[dict[str, Any], ...]
    lineage: dict[str, Any]
    review_guidance: tuple[str, ...]
    guardrail_reasons: tuple[str, ...]


class AdvisoryCopilotDraftGenerator(Protocol):
    def __call__(
        self,
        *,
        evidence_packet: CopilotEvidencePacket,
        audience: CopilotAudience,
        requested_outputs: list[str],
        requested_by: str,
        reason: dict[str, Any],
        requested_intents: tuple[str, ...] = (),
        user_instruction: str = "",
    ) -> AdvisoryCopilotDraft: ...


class PolicyEvaluationLoader(Protocol):
    def __call__(
        self,
        *,
        evaluation_status: str | None = None,
        portfolio_id: str | None = None,
    ) -> Sequence[PolicyEvaluationRecord]: ...


class AdvisoryCopilotApplicationService:
    def __init__(
        self,
        *,
        repository: AdvisoryCopilotRepository,
        draft_generator: AdvisoryCopilotDraftGenerator,
        policy_evaluation_loader: PolicyEvaluationLoader,
    ) -> None:
        self._repository = repository
        self._draft_generator = draft_generator
        self._policy_evaluation_loader = policy_evaluation_loader

    def create_evidence_packet(
        self,
        *,
        payload: AdvisoryCopilotEvidencePacketCreateRequest,
        correlation_id: str | None,
    ) -> AdvisoryCopilotEvidencePacketResponse:
        packet = build_copilot_evidence_packet(
            evidence_packet_id=payload.evidence_packet_id,
            action_family=payload.action_family,
            portfolio_id=payload.portfolio_id,
            proposal_id=payload.proposal_id,
            audience=payload.audience,
            source_sections=payload.source_sections,
        )
        record = save_advisory_copilot_evidence_packet(
            repository=self._repository,
            evidence_packet=packet,
            audience=payload.audience,
            created_by=payload.created_by,
            reason=payload.reason,
            correlation_id=resolve_advisory_copilot_correlation_id(
                correlation_id,
                fallback=f"corr-{payload.evidence_packet_id}",
            ),
        )
        return AdvisoryCopilotEvidencePacketResponse(evidence_packet=packet, record=record)

    def create_proposal_version_evidence_packet(
        self,
        *,
        payload: AdvisoryCopilotProposalVersionEvidenceRequest,
        proposal_repository: ProposalRepository,
        correlation_id: str | None,
    ) -> AdvisoryCopilotEvidencePacketResponse:
        proposal = proposal_repository.get_proposal(proposal_id=payload.proposal_id)
        if proposal is None:
            raise ValueError("COPILOT_PROPOSAL_VERSION_NOT_FOUND")
        return save_proposal_version_advisory_copilot_evidence_packet(
            repository=self._repository,
            proposal_repository=proposal_repository,
            payload=payload,
            policy_evaluations=self._policy_evaluation_loader(
                evaluation_status=None,
                portfolio_id=proposal.portfolio_id,
            ),
            correlation_id=correlation_id,
        )

    def get_evidence_packet(
        self, *, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketResponse:
        record = self._repository.get_evidence_packet(evidence_packet_id=evidence_packet_id)
        if record is None:
            raise ValueError("COPILOT_EVIDENCE_PACKET_NOT_FOUND")
        packet = load_advisory_copilot_evidence_packet(
            repository=self._repository,
            evidence_packet_id=evidence_packet_id,
        )
        return AdvisoryCopilotEvidencePacketResponse(evidence_packet=packet, record=record)

    def run_action(
        self,
        *,
        payload: AdvisoryCopilotActionRequest,
        idempotency_key: str | None,
        correlation_id: str | None,
    ) -> AdvisoryCopilotRunResponse:
        idempotency_key = normalize_optional_idempotency_key(idempotency_key)
        evidence_packet = load_advisory_copilot_evidence_packet(
            repository=self._repository,
            evidence_packet_id=payload.evidence_packet_id,
        )
        if idempotency_key:
            request_hash = build_advisory_copilot_run_request_hash(
                evidence_packet=evidence_packet,
                audience=payload.audience,
                requested_outputs=payload.requested_outputs,
                requested_by=payload.requested_by,
                reason=payload.reason,
                requested_intents=payload.requested_intents,
                user_instruction=payload.user_instruction,
            )
            replay_run = resolve_advisory_copilot_run_replay(
                repository=self._repository,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replay_run is not None:
                return AdvisoryCopilotRunResponse(run=replay_run, replayed=True)
        draft = self._draft_generator(
            evidence_packet=evidence_packet,
            audience=payload.audience,
            requested_outputs=list(payload.requested_outputs),
            requested_by=payload.requested_by,
            reason=payload.reason,
            requested_intents=payload.requested_intents,
            user_instruction=payload.user_instruction,
        )
        result = persist_advisory_copilot_run(
            repository=self._repository,
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
            correlation_id=resolve_advisory_copilot_correlation_id(
                correlation_id,
                fallback=f"corr-{payload.evidence_packet_id}",
            ),
            idempotency_key=idempotency_key,
            requested_intents=payload.requested_intents,
            user_instruction=payload.user_instruction,
        )
        return AdvisoryCopilotRunResponse(run=result.run, replayed=result.replayed)

    def get_run(self, *, run_id: str) -> AdvisoryCopilotRunResponse:
        run = self._repository.get_run(run_id=run_id)
        if run is None:
            raise ValueError("COPILOT_RUN_NOT_FOUND")
        reviews = list_advisory_copilot_reviews(repository=self._repository, run_id=run_id)
        return AdvisoryCopilotRunResponse(run=run, reviews=reviews)

    def review_run(
        self,
        *,
        run_id: str,
        payload: AdvisoryCopilotReviewRequest,
        idempotency_key: str,
        correlation_id: str | None,
    ) -> AdvisoryCopilotReviewResponse:
        idempotency_key = normalize_required_idempotency_key(idempotency_key)
        result = record_advisory_copilot_review(
            repository=self._repository,
            run_id=run_id,
            action=cast(CopilotReviewAction, payload.action),
            actor_id=payload.actor_id,
            reason=payload.reason,
            correlation_id=resolve_advisory_copilot_correlation_id(
                correlation_id,
                fallback=f"corr-{run_id}",
            ),
            idempotency_key=idempotency_key,
        )
        return AdvisoryCopilotReviewResponse(
            run=result.run,
            review=result.review,
            replayed=result.replayed,
        )

    def get_supportability(self) -> AdvisoryCopilotSupportabilityResponse:
        return build_advisory_copilot_supportability_response()

    def list_proposal_version_runs(
        self,
        *,
        proposal_id: str,
        version_id: str,
        limit: int | None,
        cursor: str | None,
    ) -> AdvisoryCopilotRunPage:
        page_size = normalize_copilot_run_page_size(limit)
        runs, next_cursor = self._repository.list_runs_for_proposal_version(
            proposal_id=proposal_id,
            proposal_version_id=version_id,
            proposal_version_no=None,
            limit=page_size,
            cursor=cursor,
        )
        return AdvisoryCopilotRunPage(
            items=tuple(runs),
            next_cursor=next_cursor,
        )
