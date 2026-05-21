from datetime import datetime, timezone
from typing import Any, Optional, cast

from src.core.proposals.activity_read_model import load_proposal_activity_read_model
from src.core.proposals.approval_read_model import load_proposal_approval_read_model
from src.core.proposals.async_operation_persistence import persist_async_operation_failed
from src.core.proposals.async_operation_read_model import (
    load_proposal_async_operation_by_correlation_read_model,
    load_proposal_async_operation_read_model,
)
from src.core.proposals.async_operation_recovery_read_model import (
    load_recoverable_async_operation_read_models,
)
from src.core.proposals.async_operation_runner import run_async_operation_until_terminal
from src.core.proposals.async_operation_submission import (
    persist_create_proposal_async_submission,
    persist_create_version_async_submission,
)
from src.core.proposals.async_operations import (
    AsyncCreateSubmissionStats,
    AsyncCreateSubmissionStatsTracker,
    build_async_replay_lineage,
    build_create_proposal_async_operation,
    build_create_version_async_operation,
)
from src.core.proposals.async_payloads import (
    AsyncCreatePayloadResolution,
    AsyncPayloadResolutionFailure,
    AsyncVersionPayloadResolution,
    hash_async_create_submission,
    hash_async_version_submission,
    resolve_async_create_payload,
    resolve_async_version_payload,
)
from src.core.proposals.async_replay import load_async_operation_replay_referents
from src.core.proposals.command_read_model import load_proposal_command_read_model
from src.core.proposals.command_validation import (
    validate_proposal_simulation_flag,
)
from src.core.proposals.context import (
    ProposalContextResolutionError,
    build_context_resolution_evidence,
    build_create_request_hash,
    build_version_request_hash,
    resolve_create_request,
    resolve_version_request,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.core.proposals.create_persistence import (
    persist_created_proposal,
    persist_created_proposal_version,
)
from src.core.proposals.delivery_summary import (
    build_delivery_history_response,
    build_delivery_summary_response,
)
from src.core.proposals.detail_read_model import load_proposal_detail_read_model
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalLifecycleError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)
from src.core.proposals.execution_handoff_command import request_proposal_execution_handoff
from src.core.proposals.execution_status import build_execution_status_response
from src.core.proposals.execution_update_command import record_proposal_execution_update
from src.core.proposals.idempotency_read_model import load_proposal_idempotency_read_model
from src.core.proposals.identifiers import (
    new_async_operation_id,
    new_proposal_id,
    new_proposal_version_id,
    new_workflow_event_id,
)
from src.core.proposals.lifecycle import (
    ProposalLifecycleOriginError,
    validate_lifecycle_origin,
)
from src.core.proposals.lifecycle_command import (
    record_proposal_approval,
    transition_proposal_state,
)
from src.core.proposals.lineage_read_model import load_proposal_lineage_read_model
from src.core.proposals.list_read_model import load_proposal_list_read_model
from src.core.proposals.materialization import build_proposal_version_materialization
from src.core.proposals.models import (
    ProposalApprovalRequest,
    ProposalApprovalsResponse,
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationRecord,
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
    ProposalReportResponse,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalVersionDetail,
    ProposalVersionRequest,
    ProposalWorkflowEventRecord,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.projections import (
    build_approvals_response,
    build_create_response_from_referents,
    build_proposal_lineage_response,
    build_proposal_list_response,
    build_workflow_timeline_response,
    to_async_accepted_response,
    to_async_status_response,
    to_create_response,
    to_idempotency_lookup_response,
    to_proposal_summary,
    to_version_detail,
)
from src.core.proposals.proposal_replay import load_proposal_version_replay_referents
from src.core.proposals.records import build_proposal_create_command_state
from src.core.proposals.report_request_command import record_proposal_report_request
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.simulation_execution import run_advisory_proposal_simulation
from src.core.proposals.version_read_model import load_proposal_version_read_model
from src.core.proposals.versions import (
    ProposalVersionConflictError,
    ProposalVersionPortfolioContextError,
    ProposalVersionTerminalStateError,
    build_new_version_created_event_and_apply_state,
    build_proposal_version_record,
    validate_create_version_portfolio_context,
    validate_create_version_state,
)
from src.core.proposals.workflow_rules import TERMINAL_STATES
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import (
    build_async_operation_replay_response,
    build_proposal_version_replay_response,
)

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
        self._validate_lifecycle_origin(
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
        )
        now = _utc_now()
        try:
            resolved_request = resolve_create_request(payload)
        except ProposalContextResolutionError as exc:
            raise ProposalValidationError(str(exc)) from exc
        request_hash = build_create_request_hash(payload=payload, resolved=resolved_request)

        idempotency_read_model = load_proposal_idempotency_read_model(
            repository=self._repository,
            idempotency_key=idempotency_key,
        )
        existing = idempotency_read_model.record
        if existing is not None:
            if existing.request_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return self._read_create_response(
                proposal_id=existing.proposal_id,
                version_no=existing.proposal_version_no,
            )

        validate_proposal_simulation_flag(
            request=resolved_request.simulate_request,
            require_simulation_flag=self._require_proposal_simulation_flag,
        )
        context_resolution = build_context_resolution_evidence(resolved_request)
        proposal_result = run_advisory_proposal_simulation(
            request=resolved_request.simulate_request,
            resolved_as_of=resolved_request.resolved_context.as_of,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            policy_context=context_resolution["advisory_policy_context"],
        )
        materialization = build_proposal_version_materialization(
            request=resolved_request.simulate_request,
            proposal_result=proposal_result,
            created_at=now,
            context_resolution=context_resolution,
            context_resolution_override=context_resolution_override,
            replay_lineage=replay_lineage,
        )

        proposal_id = new_proposal_id()
        version_no = 1
        command_state = build_proposal_create_command_state(
            proposal_id=proposal_id,
            portfolio_id=resolved_request.simulate_request.portfolio_snapshot.portfolio_id,
            mandate_id=resolved_request.metadata.mandate_id,
            jurisdiction=resolved_request.metadata.jurisdiction,
            created_by=payload.created_by,
            created_at=now,
            version_no=version_no,
            title=resolved_request.metadata.title,
            advisor_notes=resolved_request.metadata.advisor_notes,
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
            event_id=new_workflow_event_id(),
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        proposal = command_state.proposal
        version = build_proposal_version_record(
            proposal_version_id=new_proposal_version_id(),
            proposal_id=proposal_id,
            version_no=version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=materialization.artifact.model_dump(mode="json"),
            evidence_bundle=materialization.evidence_bundle,
            created_at=now,
            store_evidence_bundle=self._store_evidence_bundle,
        )
        created_event = command_state.created_event

        persist_created_proposal(
            repository=self._repository,
            command_state=command_state,
            version=version,
        )

        return to_create_response(proposal=proposal, version=version, latest_event=created_event)

    def accept_create_proposal_async_submission(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
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
        read_model = load_proposal_async_operation_read_model(
            repository=self._repository,
            operation_id=operation_id,
        )
        if read_model.operation is None:
            return
        operation = read_model.operation
        recovered_payload = self._resolve_create_async_payload(
            operation=operation,
            fallback_payload=payload,
            fallback_idempotency_key=idempotency_key,
        )
        if recovered_payload is None:
            return
        request_payload, resolved_idempotency_key = recovered_payload
        self._run_async_operation(
            operation_id=operation_id,
            executor=lambda: self.create_proposal(
                payload=request_payload,
                idempotency_key=resolved_idempotency_key,
                correlation_id=correlation_id or operation.correlation_id,
                replay_lineage=build_async_replay_lineage(operation),
            ),
        )

    def get_proposal(
        self, *, proposal_id: str, include_evidence: bool = True
    ) -> ProposalDetailResponse:
        detail = load_proposal_detail_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if detail.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        if detail.current_version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        current_version = to_version_detail(
            detail.current_version,
            include_evidence=include_evidence,
        )
        return ProposalDetailResponse(
            proposal=to_proposal_summary(detail.proposal),
            current_version=current_version,
            last_gate_decision=current_version.gate_decision,
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
        read_model = load_proposal_list_read_model(
            repository=self._repository,
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )
        return build_proposal_list_response(
            proposals=read_model.proposals,
            next_cursor=read_model.next_cursor,
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        activity = load_proposal_activity_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if activity.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        return build_workflow_timeline_response(proposal=activity.proposal, events=activity.events)

    def get_approvals(self, *, proposal_id: str) -> ProposalApprovalsResponse:
        approval_read_model = load_proposal_approval_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if approval_read_model.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        return build_approvals_response(
            proposal=approval_read_model.proposal,
            approvals=approval_read_model.approvals,
        )

    def get_lineage(self, *, proposal_id: str) -> ProposalLineageResponse:
        lineage = load_proposal_lineage_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if lineage.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        return build_proposal_lineage_response(
            proposal=lineage.proposal,
            versions_by_number=lineage.versions_by_number,
        )

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
        activity = load_proposal_activity_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if activity.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        return build_execution_status_response(proposal=activity.proposal, events=activity.events)

    def get_delivery_summary(self, *, proposal_id: str) -> ProposalDeliverySummaryResponse:
        activity = load_proposal_activity_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if activity.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        return build_delivery_summary_response(proposal=activity.proposal, events=activity.events)

    def get_delivery_history(self, *, proposal_id: str) -> ProposalDeliveryHistoryResponse:
        activity = load_proposal_activity_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if activity.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        return build_delivery_history_response(proposal=activity.proposal, events=activity.events)

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
        read_model = load_proposal_idempotency_read_model(
            repository=self._repository,
            idempotency_key=idempotency_key,
        )
        if read_model.record is None:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND")
        return to_idempotency_lookup_response(read_model.record)

    def get_async_operation(self, *, operation_id: str) -> ProposalAsyncOperationStatusResponse:
        read_model = load_proposal_async_operation_read_model(
            repository=self._repository,
            operation_id=operation_id,
        )
        if read_model.operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return to_async_status_response(read_model.operation)

    def get_async_operation_replay(self, *, operation_id: str) -> AdvisoryReplayEvidenceResponse:
        read_model = load_proposal_async_operation_read_model(
            repository=self._repository,
            operation_id=operation_id,
        )
        if read_model.operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")

        referents = load_async_operation_replay_referents(
            repository=self._repository,
            operation=read_model.operation,
        )
        return build_async_operation_replay_response(
            operation=read_model.operation,
            proposal=referents.proposal,
            version=referents.version,
            events=referents.events,
        )

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> ProposalAsyncOperationStatusResponse:
        read_model = load_proposal_async_operation_by_correlation_read_model(
            repository=self._repository,
            correlation_id=correlation_id,
        )
        if read_model.operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return to_async_status_response(read_model.operation)

    def get_version(
        self,
        *,
        proposal_id: str,
        version_no: int,
        include_evidence: bool = True,
    ) -> ProposalVersionDetail:
        read_model = load_proposal_version_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
        if read_model.version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        return to_version_detail(read_model.version, include_evidence=include_evidence)

    def create_version(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
        replay_lineage: Optional[dict[str, Any]] = None,
        context_resolution_override: Optional[dict[str, Any]] = None,
    ) -> ProposalCreateResponse:
        now = _utc_now()
        command_read_model = load_proposal_command_read_model(
            repository=self._repository,
            proposal_id=proposal_id,
        )
        if command_read_model.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        proposal = command_read_model.proposal
        try:
            validate_create_version_state(
                proposal=proposal,
                expected_current_version_no=payload.expected_current_version_no,
                terminal_states=TERMINAL_STATES,
            )
        except ProposalVersionTerminalStateError as exc:
            raise ProposalValidationError(str(exc)) from exc
        except ProposalVersionConflictError as exc:
            raise ProposalStateConflictError(str(exc)) from exc

        try:
            resolved_request = resolve_version_request(payload)
        except ProposalContextResolutionError as exc:
            raise ProposalValidationError(str(exc)) from exc
        validate_proposal_simulation_flag(
            request=resolved_request.simulate_request,
            require_simulation_flag=self._require_proposal_simulation_flag,
        )
        context_resolution = build_context_resolution_evidence(resolved_request)
        request_hash = build_version_request_hash(payload=payload, resolved=resolved_request)
        try:
            validate_create_version_portfolio_context(
                proposal_portfolio_id=proposal.portfolio_id,
                request_portfolio_id=(
                    resolved_request.simulate_request.portfolio_snapshot.portfolio_id
                ),
                allow_portfolio_id_change=self._allow_portfolio_id_change_on_new_version,
            )
        except ProposalVersionPortfolioContextError as exc:
            raise ProposalValidationError(str(exc)) from exc

        proposal_result = run_advisory_proposal_simulation(
            request=resolved_request.simulate_request,
            resolved_as_of=resolved_request.resolved_context.as_of,
            request_hash=request_hash,
            idempotency_key=None,
            correlation_id=correlation_id,
            policy_context=context_resolution["advisory_policy_context"],
        )
        materialization = build_proposal_version_materialization(
            request=resolved_request.simulate_request,
            proposal_result=proposal_result,
            created_at=now,
            context_resolution=context_resolution,
            context_resolution_override=context_resolution_override,
            replay_lineage=replay_lineage,
        )

        next_version_no = proposal.current_version_no + 1
        version = build_proposal_version_record(
            proposal_version_id=new_proposal_version_id(),
            proposal_id=proposal.proposal_id,
            version_no=next_version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=materialization.artifact.model_dump(mode="json"),
            evidence_bundle=materialization.evidence_bundle,
            created_at=now,
            store_evidence_bundle=self._store_evidence_bundle,
        )
        event = build_new_version_created_event_and_apply_state(
            event_id=new_workflow_event_id(),
            proposal=proposal,
            actor_id=payload.created_by,
            occurred_at=now,
            related_version_no=next_version_no,
            correlation_id=correlation_id,
        )
        persist_created_proposal_version(
            repository=self._repository,
            proposal=proposal,
            version=version,
            event=event,
        )
        return to_create_response(proposal=proposal, version=version, latest_event=event)

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
        read_model = load_proposal_async_operation_read_model(
            repository=self._repository,
            operation_id=operation_id,
        )
        if read_model.operation is None:
            return
        operation = read_model.operation
        recovered_payload = self._resolve_version_async_payload(
            operation=operation,
            fallback_proposal_id=proposal_id,
            fallback_payload=payload,
        )
        if recovered_payload is None:
            return
        resolved_proposal_id, request_payload = recovered_payload
        self._run_async_operation(
            operation_id=operation_id,
            executor=lambda: self.create_version(
                proposal_id=resolved_proposal_id,
                payload=request_payload,
                correlation_id=correlation_id or operation.correlation_id,
                replay_lineage=build_async_replay_lineage(operation),
            ),
        )

    def recover_async_operations(self) -> int:
        recovered = 0
        for read_model in load_recoverable_async_operation_read_models(
            repository=self._repository,
            as_of=_utc_now(),
        ):
            operation = read_model.operation
            if read_model.operation_kind == "CREATE_PROPOSAL":
                self.execute_create_proposal_async(operation_id=operation.operation_id)
                recovered += 1
                continue
            if read_model.operation_kind == "CREATE_PROPOSAL_VERSION":
                self.execute_create_version_async(operation_id=operation.operation_id)
                recovered += 1
                continue
            persist_async_operation_failed(
                repository=self._repository,
                operation=operation,
                code="ProposalLifecycleError",
                message="PROPOSAL_ASYNC_OPERATION_TYPE_UNSUPPORTED",
                finished_at=_utc_now(),
            )
        return recovered

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

    def _read_create_response(self, *, proposal_id: str, version_no: int) -> ProposalCreateResponse:
        referents = load_proposal_version_replay_referents(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
        response = build_create_response_from_referents(
            proposal=referents.proposal,
            version=referents.version,
            events=referents.events,
        )
        if response is None:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
        return response

    def _validate_lifecycle_origin(
        self,
        *,
        lifecycle_origin: ProposalLifecycleOrigin,
        source_workspace_id: Optional[str],
    ) -> None:
        try:
            validate_lifecycle_origin(
                lifecycle_origin=lifecycle_origin,
                source_workspace_id=source_workspace_id,
            )
        except ProposalLifecycleOriginError as exc:
            raise ProposalValidationError(str(exc)) from exc

    def get_version_replay(
        self,
        *,
        proposal_id: str,
        version_no: int,
    ) -> AdvisoryReplayEvidenceResponse:
        referents = load_proposal_version_replay_referents(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
        if referents.proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        if referents.version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        return build_proposal_version_replay_response(
            proposal=referents.proposal,
            version=referents.version,
            events=referents.events,
        )

    def record_report_request(
        self,
        *,
        proposal_id: str,
        report_response: ProposalReportResponse,
        requested_by: str,
        related_version_no: int,
        include_execution_summary: bool,
    ) -> ProposalWorkflowEventRecord:
        return record_proposal_report_request(
            repository=self._repository,
            proposal_id=proposal_id,
            event_id=new_workflow_event_id(),
            report_response=report_response,
            requested_by=requested_by,
            related_version_no=related_version_no,
            include_execution_summary=include_execution_summary,
        )

    def _resolve_create_async_payload(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        fallback_payload: Optional[ProposalCreateRequest],
        fallback_idempotency_key: Optional[str],
    ) -> tuple[ProposalCreateRequest, str] | None:
        resolution = resolve_async_create_payload(
            operation=operation,
            fallback_payload=fallback_payload,
            fallback_idempotency_key=fallback_idempotency_key,
        )
        if isinstance(resolution, AsyncPayloadResolutionFailure):
            persist_async_operation_failed(
                repository=self._repository,
                operation=operation,
                code=resolution.code,
                message=resolution.message,
                finished_at=_utc_now(),
            )
            return None
        resolved = cast(AsyncCreatePayloadResolution, resolution)
        return resolved.payload, resolved.idempotency_key

    def get_async_create_submission_stats_for_tests(self) -> AsyncCreateSubmissionStats:
        return self._async_create_submission_stats.snapshot()

    def _resolve_version_async_payload(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        fallback_proposal_id: Optional[str],
        fallback_payload: Optional[ProposalVersionRequest],
    ) -> tuple[str, ProposalVersionRequest] | None:
        resolution = resolve_async_version_payload(
            operation=operation,
            fallback_proposal_id=fallback_proposal_id,
            fallback_payload=fallback_payload,
        )
        if isinstance(resolution, AsyncPayloadResolutionFailure):
            persist_async_operation_failed(
                repository=self._repository,
                operation=operation,
                code=resolution.code,
                message=resolution.message,
                finished_at=_utc_now(),
            )
            return None
        resolved = cast(AsyncVersionPayloadResolution, resolution)
        return resolved.proposal_id, resolved.payload

    def _run_async_operation(
        self,
        *,
        operation_id: str,
        executor: Any,
    ) -> None:
        run_async_operation_until_terminal(
            repository=self._repository,
            operation_id=operation_id,
            executor=executor,
            utc_now=_utc_now,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
