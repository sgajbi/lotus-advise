from datetime import datetime, timezone
from typing import Any, Optional

from src.core.advisory.narrative_models import ProposalNarrativeReviewRequest
from src.core.proposals.activity_views import (
    build_delivery_history_view,
    build_delivery_summary_view,
    build_execution_status_view,
    build_workflow_timeline_view,
)
from src.core.proposals.async_operation_execution import (
    execute_create_proposal_async_operation,
    execute_create_version_async_operation,
)
from src.core.proposals.async_operation_read_model import (
    load_proposal_async_operation_by_correlation_read_model,
)
from src.core.proposals.async_operation_recovery import (
    ASYNC_RECOVERY_BATCH_SIZE,
    recover_async_operation_batch,
)
from src.core.proposals.async_operation_submission import (
    persist_create_proposal_async_submission,
    persist_create_version_async_submission,
)
from src.core.proposals.async_operation_views import (
    build_async_operation_correlation_view,
    build_async_operation_replay_view,
    build_async_operation_status_view,
)
from src.core.proposals.async_operations import (
    AsyncCreateSubmissionStats,
    AsyncCreateSubmissionStatsTracker,
    build_create_proposal_async_operation,
    build_create_version_async_operation,
)
from src.core.proposals.async_payloads import (
    hash_async_create_submission,
    hash_async_version_submission,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.core.proposals.create_command import create_proposal_command
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalLifecycleError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)
from src.core.proposals.execution_handoff_command import request_proposal_execution_handoff
from src.core.proposals.execution_update_command import record_proposal_execution_update
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key
from src.core.proposals.identifiers import (
    new_async_operation_id,
    new_workflow_event_id,
)
from src.core.proposals.lifecycle_command import (
    record_proposal_approval,
    transition_proposal_state,
)
from src.core.proposals.models import (
    ProposalApprovalRequest,
    ProposalApprovalsResponse,
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDeliveryHistoryResponse,
    ProposalDeliverySummaryResponse,
    ProposalDetailResponse,
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
    ProposalExecutionStatusResponse,
    ProposalExecutionUpdateRequest,
    ProposalIdempotencyLookupResponse,
    ProposalLifecycleOrigin,
    ProposalLineageResponse,
    ProposalListResponse,
    ProposalNarrativeReadResponse,
    ProposalNarrativeRegenerationRequest,
    ProposalNarrativeRegenerationResponse,
    ProposalNarrativeReviewResponse,
    ProposalReportResponse,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalVersionDetail,
    ProposalVersionRequest,
    ProposalWorkflowEventRecord,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.narrative_views import (
    build_narrative_view,
    record_narrative_review,
    regenerate_narrative_view,
)
from src.core.proposals.projections import (
    to_async_accepted_response,
)
from src.core.proposals.read_views import (
    build_idempotency_lookup_view,
    build_proposal_approvals_view,
    build_proposal_detail_view,
    build_proposal_lineage_view,
    build_proposal_list_view,
    build_proposal_version_view,
)
from src.core.proposals.replay_views import (
    build_proposal_version_replay_view,
)
from src.core.proposals.report_request_command import record_proposal_report_request
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.version_command import create_proposal_version
from src.core.proposals.workflow_rules import TERMINAL_STATES
from src.core.replay.models import AdvisoryReplayEvidenceResponse

ASYNC_DEFAULT_MAX_ATTEMPTS = 3

__all__ = [
    "ProposalIdempotencyConflictError",
    "ProposalLifecycleError",
    "ProposalNotFoundError",
    "ProposalStateConflictError",
    "ProposalTransitionError",
    "ProposalValidationError",
    "ProposalWorkflowService",
]


class ProposalWorkflowService:
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        store_evidence_bundle: bool = True,
        require_expected_state: bool = True,
        allow_portfolio_id_change_on_new_version: bool = False,
        require_proposal_simulation_flag: bool = True,
    ) -> None:
        self._repository = repository
        self._store_evidence_bundle = store_evidence_bundle
        self._require_expected_state = require_expected_state
        self._allow_portfolio_id_change_on_new_version = allow_portfolio_id_change_on_new_version
        self._require_proposal_simulation_flag = require_proposal_simulation_flag
        self._async_create_submission_stats = AsyncCreateSubmissionStatsTracker()

    def create_proposal(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
        lifecycle_origin: ProposalLifecycleOrigin = "DIRECT_CREATE",
        source_workspace_id: Optional[str] = None,
        replay_lineage: Optional[dict[str, Any]] = None,
        context_resolution_override: Optional[dict[str, Any]] = None,
    ) -> ProposalCreateResponse:
        return create_proposal_command(
            repository=self._repository,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
            replay_lineage=replay_lineage,
            context_resolution_override=context_resolution_override,
            store_evidence_bundle=self._store_evidence_bundle,
            require_proposal_simulation_flag=self._require_proposal_simulation_flag,
            utc_now=_utc_now,
        )

    def accept_create_proposal_async_submission(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        idempotency_key = require_proposal_idempotency_key(idempotency_key)
        submission_hash = hash_async_create_submission(payload)
        resolved_correlation_id = resolve_correlation_id(correlation_id)
        operation = build_create_proposal_async_operation(
            operation_id=new_async_operation_id(),
            correlation_id=resolved_correlation_id,
            idempotency_key=idempotency_key,
            payload=payload,
            submission_hash=submission_hash,
            created_at=_utc_now(),
            max_attempts=ASYNC_DEFAULT_MAX_ATTEMPTS,
        )
        submission_result = persist_create_proposal_async_submission(
            repository=self._repository,
            operation=operation,
            idempotency_key=idempotency_key,
            submission_hash=submission_hash,
        )
        if submission_result.is_conflict:
            self._async_create_submission_stats.record_conflict()
            raise ProposalIdempotencyConflictError(str(submission_result.conflict_message))
        self._async_create_submission_stats.record_acceptance(is_new=submission_result.is_new)
        return to_async_accepted_response(submission_result.operation), submission_result.is_new

    def submit_create_proposal_async(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        accepted, _ = self.accept_create_proposal_async_submission(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        return accepted

    def execute_create_proposal_async(
        self,
        *,
        operation_id: str,
        payload: Optional[ProposalCreateRequest] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        execute_create_proposal_async_operation(
            repository=self._repository,
            operation_id=operation_id,
            fallback_payload=payload,
            fallback_idempotency_key=idempotency_key,
            fallback_correlation_id=correlation_id,
            utc_now=_utc_now,
            create_proposal=self.create_proposal,
        )

    def get_proposal(
        self, *, proposal_id: str, include_evidence: bool = True
    ) -> ProposalDetailResponse:
        return build_proposal_detail_view(
            repository=self._repository,
            proposal_id=proposal_id,
            include_evidence=include_evidence,
        )

    def list_proposals(
        self,
        *,
        portfolio_id: Optional[str],
        state: Optional[str],
        created_by: Optional[str],
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> ProposalListResponse:
        return build_proposal_list_view(
            repository=self._repository,
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        return build_workflow_timeline_view(repository=self._repository, proposal_id=proposal_id)

    def get_approvals(self, *, proposal_id: str) -> ProposalApprovalsResponse:
        return build_proposal_approvals_view(repository=self._repository, proposal_id=proposal_id)

    def get_lineage(self, *, proposal_id: str) -> ProposalLineageResponse:
        return build_proposal_lineage_view(repository=self._repository, proposal_id=proposal_id)

    def request_execution_handoff(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionHandoffRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalExecutionHandoffResponse:
        return request_proposal_execution_handoff(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
            require_expected_state=self._require_expected_state,
            occurred_at=_utc_now(),
        )

    def get_execution_status(self, *, proposal_id: str) -> ProposalExecutionStatusResponse:
        return build_execution_status_view(repository=self._repository, proposal_id=proposal_id)

    def get_delivery_summary(self, *, proposal_id: str) -> ProposalDeliverySummaryResponse:
        return build_delivery_summary_view(repository=self._repository, proposal_id=proposal_id)

    def get_delivery_history(self, *, proposal_id: str) -> ProposalDeliveryHistoryResponse:
        return build_delivery_history_view(repository=self._repository, proposal_id=proposal_id)

    def record_execution_update(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionUpdateRequest,
    ) -> ProposalExecutionStatusResponse:
        replay_response = record_proposal_execution_update(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            terminal_states=TERMINAL_STATES,
            default_occurred_at=_utc_now(),
        )
        if replay_response is not None:
            return replay_response
        return self.get_execution_status(proposal_id=proposal_id)

    def get_idempotency_lookup(self, *, idempotency_key: str) -> ProposalIdempotencyLookupResponse:
        return build_idempotency_lookup_view(
            repository=self._repository,
            idempotency_key=idempotency_key,
        )

    def get_async_operation(self, *, operation_id: str) -> ProposalAsyncOperationStatusResponse:
        return build_async_operation_status_view(
            repository=self._repository,
            operation_id=operation_id,
        )

    def get_async_operation_replay(self, *, operation_id: str) -> AdvisoryReplayEvidenceResponse:
        return build_async_operation_replay_view(
            repository=self._repository,
            operation_id=operation_id,
        )

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> ProposalAsyncOperationStatusResponse:
        return build_async_operation_correlation_view(
            repository=self._repository,
            correlation_id=correlation_id,
        )

    def get_version(
        self,
        *,
        proposal_id: str,
        version_no: int,
        include_evidence: bool = True,
    ) -> ProposalVersionDetail:
        return build_proposal_version_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
            include_evidence=include_evidence,
        )

    def create_version(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
        replay_lineage: Optional[dict[str, Any]] = None,
        context_resolution_override: Optional[dict[str, Any]] = None,
    ) -> ProposalCreateResponse:
        return create_proposal_version(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
            replay_lineage=replay_lineage,
            context_resolution_override=context_resolution_override,
            store_evidence_bundle=self._store_evidence_bundle,
            require_proposal_simulation_flag=self._require_proposal_simulation_flag,
            allow_portfolio_id_change_on_new_version=(
                self._allow_portfolio_id_change_on_new_version
            ),
            utc_now=_utc_now,
        )

    def submit_create_version_async(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        accepted, _ = self.accept_create_version_async_submission(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )
        return accepted

    def accept_create_version_async_submission(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        resolved_correlation_id = resolve_correlation_id(correlation_id)
        submission_hash = hash_async_version_submission(
            proposal_id=proposal_id,
            payload=payload,
        )
        existing_read_model = load_proposal_async_operation_by_correlation_read_model(
            repository=self._repository, correlation_id=resolved_correlation_id
        )
        operation = build_create_version_async_operation(
            operation_id=new_async_operation_id(),
            proposal_id=proposal_id,
            correlation_id=resolved_correlation_id,
            payload=payload,
            submission_hash=submission_hash,
            created_at=_utc_now(),
            max_attempts=ASYNC_DEFAULT_MAX_ATTEMPTS,
        )
        submission_result = persist_create_version_async_submission(
            repository=self._repository,
            existing_operation=existing_read_model.operation,
            operation=operation,
            proposal_id=proposal_id,
            submission_hash=submission_hash,
        )
        if submission_result.is_conflict:
            raise ProposalIdempotencyConflictError(str(submission_result.conflict_message))
        return to_async_accepted_response(submission_result.operation), submission_result.is_new

    def execute_create_version_async(
        self,
        *,
        operation_id: str,
        proposal_id: Optional[str] = None,
        payload: Optional[ProposalVersionRequest] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        execute_create_version_async_operation(
            repository=self._repository,
            operation_id=operation_id,
            fallback_proposal_id=proposal_id,
            fallback_payload=payload,
            fallback_correlation_id=correlation_id,
            utc_now=_utc_now,
            create_version=self.create_version,
        )

    def recover_async_operations(self, *, max_operations: int = ASYNC_RECOVERY_BATCH_SIZE) -> int:
        return recover_async_operation_batch(
            repository=self._repository,
            max_operations=max_operations,
            utc_now=_utc_now,
            execute_create_proposal_async=self.execute_create_proposal_async,
            execute_create_version_async=self.execute_create_version_async,
        )

    def transition_state(
        self,
        *,
        proposal_id: str,
        payload: ProposalStateTransitionRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        return transition_proposal_state(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
            require_expected_state=self._require_expected_state,
            occurred_at=_utc_now(),
        )

    def record_approval(
        self,
        *,
        proposal_id: str,
        payload: ProposalApprovalRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        return record_proposal_approval(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
            require_expected_state=self._require_expected_state,
            occurred_at=_utc_now(),
        )

    def get_version_replay(
        self,
        *,
        proposal_id: str,
        version_no: int,
    ) -> AdvisoryReplayEvidenceResponse:
        return build_proposal_version_replay_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )

    def get_narrative(
        self,
        *,
        proposal_id: str,
        version_no: int,
    ) -> ProposalNarrativeReadResponse:
        return build_narrative_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )

    def regenerate_narrative(
        self,
        *,
        proposal_id: str,
        version_no: int,
        payload: ProposalNarrativeRegenerationRequest,
    ) -> ProposalNarrativeRegenerationResponse:
        return regenerate_narrative_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
        )

    def record_narrative_review(
        self,
        *,
        proposal_id: str,
        version_no: int,
        payload: ProposalNarrativeReviewRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalNarrativeReviewResponse:
        return record_narrative_review(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_workflow_event_id(),
            occurred_at=_utc_now,
        )

    def record_report_request(
        self,
        *,
        proposal_id: str,
        report_response: ProposalReportResponse,
        requested_by: str,
        related_version_no: int,
        include_execution_summary: bool,
        include_reviewed_narrative: bool = False,
        proposal_narrative_package: dict[str, Any] | None = None,
    ) -> ProposalWorkflowEventRecord:
        return record_proposal_report_request(
            repository=self._repository,
            proposal_id=proposal_id,
            event_id=new_workflow_event_id(),
            report_response=report_response,
            requested_by=requested_by,
            related_version_no=related_version_no,
            include_execution_summary=include_execution_summary,
            include_reviewed_narrative=include_reviewed_narrative,
            proposal_narrative_package=proposal_narrative_package,
        )

    def get_async_create_submission_stats_for_tests(self) -> AsyncCreateSubmissionStats:
        return self._async_create_submission_stats.snapshot()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
