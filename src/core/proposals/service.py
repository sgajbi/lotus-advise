from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Optional, cast

from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.advisory.risk_lens import extract_risk_lens
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals.async_operations import (
    apply_runtime_exception_outcome,
    begin_async_attempt,
    build_async_replay_lineage,
    mark_operation_failed,
    mark_operation_succeeded,
)
from src.core.proposals.async_payloads import (
    AsyncCreatePayloadResolution,
    AsyncPayloadResolutionFailure,
    AsyncVersionPayloadResolution,
    extract_async_submission_hash,
    resolve_async_create_payload,
    resolve_async_version_payload,
)
from src.core.proposals.async_payloads import (
    hash_async_create_submission as build_async_create_submission_hash,
)
from src.core.proposals.async_payloads import (
    hash_async_version_submission as build_async_version_submission_hash,
)
from src.core.proposals.concurrency import (
    ProposalExpectedStateError,
    validate_expected_state,
)
from src.core.proposals.context import (
    ProposalContextResolutionError,
    build_context_resolution_evidence,
    canonicalize_create_request_payload,
    canonicalize_version_request_payload,
    resolve_create_request,
    resolve_version_request,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.core.proposals.delivery_summary import (
    build_delivery_summary_from_events,
    select_delivery_events,
)
from src.core.proposals.execution_status import (
    build_execution_status_response,
    latest_execution_requested_event,
)
from src.core.proposals.idempotency import (
    ProposalReplayHashConflictError,
    find_replayed_approval,
    find_replayed_event,
)
from src.core.proposals.identifiers import (
    new_approval_id,
    new_async_operation_id,
    new_execution_request_id,
    new_proposal_id,
    new_proposal_version_id,
    new_workflow_event_id,
)
from src.core.proposals.lifecycle import (
    ProposalLifecycleOriginError,
    validate_lifecycle_origin,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalApprovalsResponse,
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationRecord,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDeliveryExecutionSummary,
    ProposalDeliveryHistoryResponse,
    ProposalDeliveryReportingSummary,
    ProposalDeliverySummaryResponse,
    ProposalDetailResponse,
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
    ProposalExecutionStatusResponse,
    ProposalExecutionUpdateRequest,
    ProposalIdempotencyLookupResponse,
    ProposalIdempotencyRecord,
    ProposalLifecycleOrigin,
    ProposalLineageResponse,
    ProposalListResponse,
    ProposalRecord,
    ProposalReportResponse,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalVersionDetail,
    ProposalVersionLineageItem,
    ProposalVersionRequest,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.projections import (
    to_approval_record,
    to_async_accepted_response,
    to_async_status_response,
    to_create_response,
    to_proposal_summary,
    to_version_detail,
    to_workflow_event,
)
from src.core.proposals.reporting import build_report_requested_event
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.simulation_gate import (
    ProposalSimulationGateError,
    validate_proposal_simulation_enabled,
)
from src.core.proposals.versions import build_proposal_version_record
from src.core.proposals.workflow_rules import (
    TERMINAL_STATES,
    ProposalWorkflowRuleError,
    resolve_execution_update_event,
)
from src.core.proposals.workflow_rules import (
    resolve_approval_transition as build_approval_transition,
)
from src.core.proposals.workflow_rules import (
    resolve_transition_state as build_transition_state,
)
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import (
    build_async_operation_replay_response,
    build_proposal_version_replay_response,
)

ASYNC_DEFAULT_MAX_ATTEMPTS = 3
ASYNC_OPERATION_LEASE_SECONDS = 60
ASYNC_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED"}


class ProposalLifecycleError(Exception):
    pass


class ProposalNotFoundError(ProposalLifecycleError):
    pass


class ProposalValidationError(ProposalLifecycleError):
    pass


class ProposalIdempotencyConflictError(ProposalLifecycleError):
    pass


class ProposalStateConflictError(ProposalLifecycleError):
    pass


class ProposalTransitionError(ProposalLifecycleError):
    pass


@dataclass(frozen=True)
class AsyncCreateSubmissionStats:
    accepted_new: int
    accepted_replayed: int
    conflicts: int


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
        self._async_create_submission_stats_lock = RLock()
        self._async_create_submission_stats = {
            "accepted_new": 0,
            "accepted_replayed": 0,
            "conflicts": 0,
        }

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
        request_payload = canonicalize_create_request_payload(
            payload=payload,
            resolved=resolved_request,
        )
        request_hash = hash_canonical_payload(request_payload)

        existing = self._repository.get_idempotency(idempotency_key=idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return self._read_create_response(
                proposal_id=existing.proposal_id,
                version_no=existing.proposal_version_no,
            )

        self._validate_simulation_flag(resolved_request.simulate_request)
        context_resolution = build_context_resolution_evidence(resolved_request)
        proposal_result = self._run_simulation(
            request=resolved_request.simulate_request,
            resolved_as_of=resolved_request.resolved_context.as_of,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            policy_context=context_resolution["advisory_policy_context"],
        )
        artifact = build_proposal_artifact(
            request=resolved_request.simulate_request,
            proposal_result=proposal_result,
            created_at=now.isoformat(),
        )
        evidence_bundle = artifact.evidence_bundle.model_dump(mode="json")
        evidence_bundle["context_resolution"] = (
            dict(context_resolution_override)
            if context_resolution_override is not None
            else context_resolution
        )
        evidence_bundle["risk_lens"] = extract_risk_lens(proposal_result)
        if replay_lineage:
            evidence_bundle["replay_lineage"] = dict(replay_lineage)

        proposal_id = new_proposal_id()
        version_no = 1
        proposal = ProposalRecord(
            proposal_id=proposal_id,
            portfolio_id=resolved_request.simulate_request.portfolio_snapshot.portfolio_id,
            mandate_id=resolved_request.metadata.mandate_id,
            jurisdiction=resolved_request.metadata.jurisdiction,
            created_by=payload.created_by,
            created_at=now,
            last_event_at=now,
            current_state="DRAFT",
            current_version_no=version_no,
            title=resolved_request.metadata.title,
            advisor_notes=resolved_request.metadata.advisor_notes,
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
        )
        version = build_proposal_version_record(
            proposal_version_id=new_proposal_version_id(),
            proposal_id=proposal_id,
            version_no=version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=artifact.model_dump(mode="json"),
            evidence_bundle=evidence_bundle,
            created_at=now,
            store_evidence_bundle=self._store_evidence_bundle,
        )
        created_event = ProposalWorkflowEventRecord(
            event_id=new_workflow_event_id(),
            proposal_id=proposal_id,
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id=payload.created_by,
            occurred_at=now,
            reason_json={"correlation_id": correlation_id} if correlation_id else {},
            related_version_no=version_no,
        )

        self._repository.create_proposal(proposal)
        self._repository.create_version(version)
        self._repository.append_event(created_event)
        self._repository.save_idempotency(
            ProposalIdempotencyRecord(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                proposal_id=proposal_id,
                proposal_version_no=version_no,
                created_at=now,
            )
        )

        return to_create_response(proposal=proposal, version=version, latest_event=created_event)

    def accept_create_proposal_async_submission(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        submission_hash = self._hash_async_create_submission(payload)
        resolved_correlation_id = resolve_correlation_id(correlation_id)
        operation = ProposalAsyncOperationRecord(
            operation_id=new_async_operation_id(),
            operation_type="CREATE_PROPOSAL",
            status="PENDING",
            correlation_id=resolved_correlation_id,
            idempotency_key=idempotency_key,
            proposal_id=None,
            created_by=payload.created_by,
            created_at=_utc_now(),
            payload_json={
                "payload": payload.model_dump(mode="json"),
                "idempotency_key": idempotency_key,
                "submission_hash": submission_hash,
            },
            attempt_count=0,
            max_attempts=ASYNC_DEFAULT_MAX_ATTEMPTS,
            started_at=None,
            lease_expires_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
        )
        stored_operation, is_new = self._repository.create_operation_if_absent_by_idempotency(
            operation
        )
        if not is_new:
            existing_hash = extract_async_submission_hash(stored_operation)
            if existing_hash != submission_hash:
                self._record_async_create_submission_outcome("conflicts")
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: async submission hash mismatch"
                )
        self._record_async_create_submission_outcome(
            "accepted_new" if is_new else "accepted_replayed"
        )
        return to_async_accepted_response(stored_operation), is_new

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
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            return
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
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        version = self._repository.get_current_version(proposal_id=proposal_id)
        if version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        current_version = to_version_detail(version, include_evidence=include_evidence)
        return ProposalDetailResponse(
            proposal=to_proposal_summary(proposal),
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
        rows, next_cursor = self._repository.list_proposals(
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )
        return ProposalListResponse(
            items=[to_proposal_summary(row) for row in rows], next_cursor=next_cursor
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        events = self._repository.list_events(proposal_id=proposal_id)
        timeline_events = [to_workflow_event(event) for event in events]
        return ProposalWorkflowTimelineResponse(
            proposal=to_proposal_summary(proposal),
            current_state=proposal.current_state,
            event_count=len(timeline_events),
            latest_event=timeline_events[-1] if timeline_events else None,
            events=timeline_events,
        )

    def get_approvals(self, *, proposal_id: str) -> ProposalApprovalsResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        approvals = [
            to_approval_record(approval)
            for approval in self._repository.list_approvals(proposal_id=proposal_id)
            if approval is not None
        ]
        latest_approval = approvals[-1] if approvals else None
        return ProposalApprovalsResponse(
            proposal=to_proposal_summary(proposal),
            approval_count=len(approvals),
            latest_approval_at=latest_approval.occurred_at if latest_approval is not None else None,
            approvals=approvals,
        )

    def get_lineage(self, *, proposal_id: str) -> ProposalLineageResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        versions: list[ProposalVersionLineageItem] = []
        missing_version_numbers: list[int] = []
        for version_no in range(1, proposal.current_version_no + 1):
            version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
            if version is None:
                missing_version_numbers.append(version_no)
                continue
            versions.append(
                ProposalVersionLineageItem(
                    proposal_version_id=version.proposal_version_id,
                    version_no=version.version_no,
                    created_at=version.created_at.isoformat(),
                    status_at_creation=version.status_at_creation,
                    request_hash=version.request_hash,
                    simulation_hash=version.simulation_hash,
                    artifact_hash=version.artifact_hash,
                )
            )

        latest_version = versions[-1] if versions else None
        return ProposalLineageResponse(
            proposal=to_proposal_summary(proposal),
            version_count=len(versions),
            latest_version_no=latest_version.version_no if latest_version is not None else None,
            latest_version_created_at=(
                latest_version.created_at if latest_version is not None else None
            ),
            lineage_complete=not missing_version_numbers,
            missing_version_numbers=missing_version_numbers,
            versions=versions,
        )

    def request_execution_handoff(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionHandoffRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalExecutionHandoffResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        replay_event = self._get_replayed_event(
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_event is not None:
            return ProposalExecutionHandoffResponse(
                proposal=to_proposal_summary(proposal),
                execution_request_id=(
                    str(replay_event.reason_json.get("execution_request_id"))
                    if replay_event.reason_json.get("execution_request_id") is not None
                    else ""
                ),
                handoff_status="REQUESTED",
                execution_provider=str(replay_event.reason_json.get("execution_provider")),
                latest_workflow_event=to_workflow_event(replay_event),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)
        if proposal.current_state != "EXECUTION_READY":
            raise ProposalStateConflictError(
                "STATE_CONFLICT: proposal must be EXECUTION_READY for execution handoff"
            )

        occurred_at = _utc_now()
        execution_request_id = payload.external_request_id or new_execution_request_id()
        reason_json = {
            "execution_request_id": execution_request_id,
            "execution_provider": payload.execution_provider,
            "correlation_id": payload.correlation_id,
            "external_request_id": payload.external_request_id,
            "notes": payload.notes,
        }
        if idempotency_key:
            reason_json["idempotency_key"] = idempotency_key
            reason_json["idempotency_request_hash"] = request_hash
        event = ProposalWorkflowEventRecord(
            event_id=new_workflow_event_id(),
            proposal_id=proposal_id,
            event_type="EXECUTION_REQUESTED",
            from_state=proposal.current_state,
            to_state="EXECUTION_READY",
            actor_id=payload.actor_id,
            occurred_at=occurred_at,
            reason_json={k: v for k, v in reason_json.items() if v is not None},
            related_version_no=payload.related_version_no or proposal.current_version_no,
        )
        proposal.last_event_at = occurred_at
        result = self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return ProposalExecutionHandoffResponse(
            proposal=to_proposal_summary(result.proposal),
            execution_request_id=execution_request_id,
            handoff_status="REQUESTED",
            execution_provider=payload.execution_provider,
            latest_workflow_event=to_workflow_event(result.event),
        )

    def get_execution_status(self, *, proposal_id: str) -> ProposalExecutionStatusResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        events = self._repository.list_events(proposal_id=proposal_id)
        return build_execution_status_response(proposal=proposal, events=events)

    def get_delivery_summary(self, *, proposal_id: str) -> ProposalDeliverySummaryResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        events = self._repository.list_events(proposal_id=proposal_id)
        delivery = build_delivery_summary_from_events(events)
        execution_payload = delivery.get("execution")
        reporting_payload = delivery.get("reporting")
        return ProposalDeliverySummaryResponse(
            proposal=to_proposal_summary(proposal),
            execution=(
                ProposalDeliveryExecutionSummary.model_validate(execution_payload)
                if isinstance(execution_payload, dict)
                else None
            ),
            reporting=(
                ProposalDeliveryReportingSummary.model_validate(reporting_payload)
                if isinstance(reporting_payload, dict)
                else None
            ),
            explanation={
                "source": "ADVISORY_WORKFLOW_EVENTS",
                "delivery_projection": "LATEST_EXECUTION_AND_REPORTING_POSTURE",
            },
        )

    def get_delivery_history(self, *, proposal_id: str) -> ProposalDeliveryHistoryResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        events = select_delivery_events(self._repository.list_events(proposal_id=proposal_id))
        history_events = [to_workflow_event(event) for event in events]
        return ProposalDeliveryHistoryResponse(
            proposal=to_proposal_summary(proposal),
            event_count=len(history_events),
            latest_event=history_events[-1] if history_events else None,
            events=history_events,
            explanation={
                "source": "ADVISORY_WORKFLOW_EVENTS",
                "filter": "DELIVERY_ONLY",
            },
        )

    def record_execution_update(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionUpdateRequest,
    ) -> ProposalExecutionStatusResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        events = self._repository.list_events(proposal_id=proposal_id)
        latest_execution_requested = latest_execution_requested_event(events)
        if latest_execution_requested is None:
            raise ProposalValidationError("EXECUTION_HANDOFF_NOT_FOUND")

        expected_execution_request_id = latest_execution_requested.reason_json.get(
            "execution_request_id"
        )
        if expected_execution_request_id != payload.execution_request_id:
            raise ProposalStateConflictError("EXECUTION_REQUEST_ID_MISMATCH")
        expected_execution_provider = latest_execution_requested.reason_json.get(
            "execution_provider"
        )
        if expected_execution_provider != payload.execution_provider:
            raise ProposalStateConflictError("EXECUTION_PROVIDER_MISMATCH")

        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        replay_event = self._get_replayed_event(
            proposal_id=proposal_id,
            idempotency_key=f"execution-update:{payload.update_id}",
            request_hash=request_hash,
        )
        if replay_event is not None:
            return self.get_execution_status(proposal_id=proposal_id)

        event_type, to_state = resolve_execution_update_event(payload.update_status)
        if proposal.current_state in TERMINAL_STATES:
            raise ProposalStateConflictError("PROPOSAL_TERMINAL_STATE: execution update rejected")

        occurred_at = (
            datetime.fromisoformat(payload.occurred_at)
            if payload.occurred_at is not None
            else _utc_now()
        )
        if occurred_at < latest_execution_requested.occurred_at:
            raise ProposalValidationError("EXECUTION_UPDATE_OCCURRED_BEFORE_HANDOFF")
        reason_json = {
            "update_id": payload.update_id,
            "execution_request_id": payload.execution_request_id,
            "execution_provider": payload.execution_provider,
            "external_execution_id": payload.external_execution_id,
            "details": payload.details,
            "idempotency_key": f"execution-update:{payload.update_id}",
            "idempotency_request_hash": request_hash,
        }
        event = ProposalWorkflowEventRecord(
            event_id=new_workflow_event_id(),
            proposal_id=proposal_id,
            event_type=event_type,
            from_state=proposal.current_state,
            to_state=to_state,
            actor_id=payload.actor_id,
            occurred_at=occurred_at,
            reason_json={k: v for k, v in reason_json.items() if v is not None},
            related_version_no=(
                payload.related_version_no or latest_execution_requested.related_version_no
            ),
        )
        proposal.current_state = to_state
        proposal.last_event_at = occurred_at
        self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return self.get_execution_status(proposal_id=proposal_id)

    def get_idempotency_lookup(self, *, idempotency_key: str) -> ProposalIdempotencyLookupResponse:
        record = self._repository.get_idempotency(idempotency_key=idempotency_key)
        if record is None:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND")
        return ProposalIdempotencyLookupResponse(
            idempotency_key=record.idempotency_key,
            request_hash=record.request_hash,
            proposal_id=record.proposal_id,
            proposal_version_no=record.proposal_version_no,
            created_at=record.created_at.isoformat(),
        )

    def get_async_operation(self, *, operation_id: str) -> ProposalAsyncOperationStatusResponse:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return to_async_status_response(operation)

    def get_async_operation_replay(self, *, operation_id: str) -> AdvisoryReplayEvidenceResponse:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")

        proposal = None
        version = None
        events: list[ProposalWorkflowEventRecord] | None = None
        if operation.proposal_id is not None:
            proposal = self._repository.get_proposal(proposal_id=operation.proposal_id)
            if proposal is not None and operation.status == "SUCCEEDED":
                version_no = None
                if operation.result_json is not None:
                    version_payload = operation.result_json.get("version")
                    if isinstance(version_payload, dict) and isinstance(
                        version_payload.get("version_no"), int
                    ):
                        version_no = version_payload["version_no"]
                if version_no is not None:
                    version = self._repository.get_version(
                        proposal_id=operation.proposal_id,
                        version_no=version_no,
                    )
                if version is None:
                    version = self._repository.get_current_version(
                        proposal_id=operation.proposal_id
                    )
            if proposal is not None:
                events = self._repository.list_events(proposal_id=operation.proposal_id)
        return build_async_operation_replay_response(
            operation=operation,
            proposal=proposal,
            version=version,
            events=events,
        )

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> ProposalAsyncOperationStatusResponse:
        operation = self._repository.get_operation_by_correlation(correlation_id=correlation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return to_async_status_response(operation)

    def get_version(
        self,
        *,
        proposal_id: str,
        version_no: int,
        include_evidence: bool = True,
    ) -> ProposalVersionDetail:
        version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
        if version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        return to_version_detail(version, include_evidence=include_evidence)

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
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        if proposal.current_state in TERMINAL_STATES:
            raise ProposalValidationError("PROPOSAL_TERMINAL_STATE: cannot create version")
        if (
            payload.expected_current_version_no is not None
            and payload.expected_current_version_no != proposal.current_version_no
        ):
            raise ProposalStateConflictError(
                "VERSION_CONFLICT: expected_current_version_no mismatch"
            )

        try:
            resolved_request = resolve_version_request(payload)
        except ProposalContextResolutionError as exc:
            raise ProposalValidationError(str(exc)) from exc
        self._validate_simulation_flag(resolved_request.simulate_request)
        context_resolution = build_context_resolution_evidence(resolved_request)
        request_hash = hash_canonical_payload(
            canonicalize_version_request_payload(
                payload=payload,
                resolved=resolved_request,
            )
        )
        if (
            not self._allow_portfolio_id_change_on_new_version
            and resolved_request.simulate_request.portfolio_snapshot.portfolio_id
            != proposal.portfolio_id
        ):
            raise ProposalValidationError("PORTFOLIO_CONTEXT_MISMATCH")

        proposal_result = self._run_simulation(
            request=resolved_request.simulate_request,
            resolved_as_of=resolved_request.resolved_context.as_of,
            request_hash=request_hash,
            idempotency_key=None,
            correlation_id=correlation_id,
            policy_context=context_resolution["advisory_policy_context"],
        )
        artifact = build_proposal_artifact(
            request=resolved_request.simulate_request,
            proposal_result=proposal_result,
            created_at=now.isoformat(),
        )
        evidence_bundle = artifact.evidence_bundle.model_dump(mode="json")
        evidence_bundle["context_resolution"] = (
            dict(context_resolution_override)
            if context_resolution_override is not None
            else context_resolution
        )
        evidence_bundle["risk_lens"] = extract_risk_lens(proposal_result)
        if replay_lineage:
            evidence_bundle["replay_lineage"] = dict(replay_lineage)

        next_version_no = proposal.current_version_no + 1
        reset_state: ProposalWorkflowState = "DRAFT"
        version = build_proposal_version_record(
            proposal_version_id=new_proposal_version_id(),
            proposal_id=proposal.proposal_id,
            version_no=next_version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=artifact.model_dump(mode="json"),
            evidence_bundle=evidence_bundle,
            created_at=now,
            store_evidence_bundle=self._store_evidence_bundle,
        )
        event = ProposalWorkflowEventRecord(
            event_id=new_workflow_event_id(),
            proposal_id=proposal.proposal_id,
            event_type="NEW_VERSION_CREATED",
            from_state=proposal.current_state,
            to_state=reset_state,
            actor_id=payload.created_by,
            occurred_at=now,
            reason_json={"correlation_id": correlation_id} if correlation_id else {},
            related_version_no=next_version_no,
        )

        proposal.current_version_no = next_version_no
        proposal.current_state = reset_state
        proposal.last_event_at = now
        self._repository.create_version(version)
        self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
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
        submission_hash = self._hash_async_version_submission(
            proposal_id=proposal_id,
            payload=payload,
        )
        existing_operation = self._repository.get_operation_by_correlation(
            correlation_id=resolved_correlation_id
        )
        if existing_operation is not None:
            existing_hash = extract_async_submission_hash(existing_operation)
            if (
                existing_operation.operation_type != "CREATE_PROPOSAL_VERSION"
                or existing_operation.proposal_id != proposal_id
                or existing_hash != submission_hash
            ):
                raise ProposalIdempotencyConflictError(
                    "CORRELATION_ID_CONFLICT: async version submission mismatch"
                )
            return to_async_accepted_response(existing_operation), False
        operation = ProposalAsyncOperationRecord(
            operation_id=new_async_operation_id(),
            operation_type="CREATE_PROPOSAL_VERSION",
            status="PENDING",
            correlation_id=resolved_correlation_id,
            idempotency_key=None,
            proposal_id=proposal_id,
            created_by=payload.created_by,
            created_at=_utc_now(),
            payload_json={
                "proposal_id": proposal_id,
                "payload": payload.model_dump(mode="json"),
                "submission_hash": submission_hash,
            },
            attempt_count=0,
            max_attempts=ASYNC_DEFAULT_MAX_ATTEMPTS,
            started_at=None,
            lease_expires_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
        )
        self._repository.create_operation(operation)
        return to_async_accepted_response(operation), True

    def execute_create_version_async(
        self,
        *,
        operation_id: str,
        proposal_id: Optional[str] = None,
        payload: Optional[ProposalVersionRequest] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            return
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
        for operation in self._repository.list_recoverable_operations(as_of=_utc_now()):
            if operation.operation_type == "CREATE_PROPOSAL":
                self.execute_create_proposal_async(operation_id=operation.operation_id)
                recovered += 1
                continue
            if operation.operation_type == "CREATE_PROPOSAL_VERSION":
                self.execute_create_version_async(operation_id=operation.operation_id)
                recovered += 1
                continue
            self._mark_operation_failed(
                operation=operation,
                code="ProposalLifecycleError",
                message="PROPOSAL_ASYNC_OPERATION_TYPE_UNSUPPORTED",
            )
        return recovered

    def transition_state(
        self,
        *,
        proposal_id: str,
        payload: ProposalStateTransitionRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        replay_event = self._get_replayed_event(
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_event is not None:
            return ProposalStateTransitionResponse(
                proposal_id=proposal_id,
                current_state=replay_event.to_state,
                latest_workflow_event=to_workflow_event(replay_event),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)

        to_state = self._resolve_transition_state(
            current_state=proposal.current_state,
            event_type=payload.event_type,
        )
        reason_json = dict(payload.reason)
        if idempotency_key:
            reason_json["idempotency_key"] = idempotency_key
            reason_json["idempotency_request_hash"] = request_hash
        event = ProposalWorkflowEventRecord(
            event_id=new_workflow_event_id(),
            proposal_id=proposal_id,
            event_type=payload.event_type,
            from_state=proposal.current_state,
            to_state=to_state,
            actor_id=payload.actor_id,
            occurred_at=_utc_now(),
            reason_json=reason_json,
            related_version_no=payload.related_version_no,
        )
        proposal.current_state = to_state
        proposal.last_event_at = event.occurred_at

        result = self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return ProposalStateTransitionResponse(
            proposal_id=proposal_id,
            current_state=result.proposal.current_state,
            latest_workflow_event=to_workflow_event(result.event),
        )

    def record_approval(
        self,
        *,
        proposal_id: str,
        payload: ProposalApprovalRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        replay_approval = self._get_replayed_approval(
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_approval is not None:
            replay_event = self._get_replayed_event(
                proposal_id=proposal_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replay_event is None:
                raise ProposalLifecycleError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
            return ProposalStateTransitionResponse(
                proposal_id=proposal_id,
                current_state=replay_event.to_state,
                latest_workflow_event=to_workflow_event(replay_event),
                approval=to_approval_record(replay_approval),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)

        details_json = dict(payload.details)
        if idempotency_key:
            details_json["idempotency_key"] = idempotency_key
            details_json["idempotency_request_hash"] = request_hash
        approval = ProposalApprovalRecordData(
            approval_id=new_approval_id(),
            proposal_id=proposal_id,
            approval_type=payload.approval_type,
            approved=payload.approved,
            actor_id=payload.actor_id,
            occurred_at=_utc_now(),
            details_json=details_json,
            related_version_no=payload.related_version_no,
        )

        event_type, to_state = self._resolve_approval_transition(
            current_state=proposal.current_state,
            approval_type=payload.approval_type,
            approved=payload.approved,
        )
        reason_json = dict(payload.details)
        if idempotency_key:
            reason_json["idempotency_key"] = idempotency_key
            reason_json["idempotency_request_hash"] = request_hash
        event = ProposalWorkflowEventRecord(
            event_id=new_workflow_event_id(),
            proposal_id=proposal_id,
            event_type=event_type,
            from_state=proposal.current_state,
            to_state=to_state,
            actor_id=payload.actor_id,
            occurred_at=approval.occurred_at,
            reason_json=reason_json,
            related_version_no=payload.related_version_no,
        )
        proposal.current_state = to_state
        proposal.last_event_at = event.occurred_at

        result = self._repository.transition_proposal(
            proposal=proposal, event=event, approval=approval
        )
        return ProposalStateTransitionResponse(
            proposal_id=proposal_id,
            current_state=result.proposal.current_state,
            latest_workflow_event=to_workflow_event(result.event),
            approval=to_approval_record(result.approval),
        )

    def _get_replayed_event(
        self, *, proposal_id: str, idempotency_key: Optional[str], request_hash: str
    ) -> Optional[ProposalWorkflowEventRecord]:
        try:
            return find_replayed_event(
                events=self._repository.list_events(proposal_id=proposal_id),
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        except ProposalReplayHashConflictError as exc:
            raise ProposalIdempotencyConflictError(str(exc)) from exc

    def _get_replayed_approval(
        self, *, proposal_id: str, idempotency_key: Optional[str], request_hash: str
    ) -> Optional[ProposalApprovalRecordData]:
        try:
            return find_replayed_approval(
                approvals=self._repository.list_approvals(proposal_id=proposal_id),
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        except ProposalReplayHashConflictError as exc:
            raise ProposalIdempotencyConflictError(str(exc)) from exc

    def _read_create_response(self, *, proposal_id: str, version_no: int) -> ProposalCreateResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
        events = self._repository.list_events(proposal_id=proposal_id)
        if proposal is None or version is None or not events:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
        return to_create_response(proposal=proposal, version=version, latest_event=events[-1])

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
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
        if version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        events = self._repository.list_events(proposal_id=proposal_id)
        return build_proposal_version_replay_response(
            proposal=proposal,
            version=version,
            events=events,
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
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        event = build_report_requested_event(
            event_id=new_workflow_event_id(),
            proposal=proposal,
            report_response=report_response,
            requested_by=requested_by,
            related_version_no=related_version_no,
            include_execution_summary=include_execution_summary,
        )
        proposal.last_event_at = max(proposal.last_event_at, event.occurred_at)
        self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return event

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
            self._mark_operation_failed(
                operation=operation,
                code=resolution.code,
                message=resolution.message,
            )
            return None
        resolved = cast(AsyncCreatePayloadResolution, resolution)
        return resolved.payload, resolved.idempotency_key

    def _hash_async_create_submission(self, payload: ProposalCreateRequest) -> str:
        return cast(str, build_async_create_submission_hash(payload))

    def _hash_async_version_submission(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
    ) -> str:
        return cast(
            str,
            build_async_version_submission_hash(proposal_id=proposal_id, payload=payload),
        )

    def _record_async_create_submission_outcome(self, key: str) -> None:
        with self._async_create_submission_stats_lock:
            self._async_create_submission_stats[key] += 1

    def get_async_create_submission_stats_for_tests(self) -> AsyncCreateSubmissionStats:
        with self._async_create_submission_stats_lock:
            return AsyncCreateSubmissionStats(
                accepted_new=self._async_create_submission_stats["accepted_new"],
                accepted_replayed=self._async_create_submission_stats["accepted_replayed"],
                conflicts=self._async_create_submission_stats["conflicts"],
            )

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
            self._mark_operation_failed(
                operation=operation,
                code=resolution.code,
                message=resolution.message,
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
        while True:
            operation = self._repository.get_operation(operation_id=operation_id)
            if operation is None or operation.status in ASYNC_TERMINAL_STATUSES:
                return

            self._begin_async_attempt(operation)
            try:
                response = executor()
            except ProposalLifecycleError as exc:
                self._mark_operation_failed(
                    operation=operation,
                    code=type(exc).__name__,
                    message=str(exc),
                )
                return
            except Exception as exc:
                if self._requeue_or_fail_runtime_exception(operation=operation, exc=exc):
                    continue
                return

            self._mark_operation_succeeded(operation=operation, response=response)
            return

    def _begin_async_attempt(self, operation: ProposalAsyncOperationRecord) -> None:
        begin_async_attempt(
            operation=operation,
            attempt_started_at=_utc_now(),
            lease_seconds=ASYNC_OPERATION_LEASE_SECONDS,
        )
        self._repository.update_operation(operation)

    def _mark_operation_succeeded(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        response: ProposalCreateResponse,
    ) -> None:
        mark_operation_succeeded(
            operation=operation,
            response=response,
            finished_at=_utc_now(),
        )
        self._repository.update_operation(operation)

    def _mark_operation_failed(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        code: str,
        message: str,
    ) -> None:
        mark_operation_failed(
            operation=operation,
            code=code,
            message=message,
            finished_at=_utc_now(),
        )
        self._repository.update_operation(operation)

    def _requeue_or_fail_runtime_exception(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        exc: Exception,
    ) -> bool:
        should_requeue = apply_runtime_exception_outcome(
            operation=operation,
            exc=exc,
            finished_at=_utc_now(),
        )
        self._repository.update_operation(operation)
        return cast(bool, should_requeue)

    def _run_simulation(
        self,
        *,
        request: ProposalSimulateRequest,
        resolved_as_of: str,
        request_hash: str,
        idempotency_key: Optional[str],
        correlation_id: Optional[str],
        policy_context: Optional[dict[str, Any]] = None,
    ) -> ProposalResult:
        resolved_correlation_id = resolve_correlation_id(correlation_id)
        return evaluate_advisory_proposal(
            request=request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=resolved_correlation_id,
            resolved_as_of=resolved_as_of,
            policy_context=policy_context,
        )

    def _validate_simulation_flag(self, request: ProposalSimulateRequest) -> None:
        try:
            validate_proposal_simulation_enabled(
                request=request,
                require_simulation_flag=self._require_proposal_simulation_flag,
            )
        except ProposalSimulationGateError as exc:
            raise ProposalValidationError(str(exc)) from exc

    def _validate_expected_state(
        self,
        current_state: ProposalWorkflowState,
        expected_state: Optional[ProposalWorkflowState],
    ) -> None:
        try:
            validate_expected_state(
                current_state=current_state,
                expected_state=expected_state,
                require_expected_state=self._require_expected_state,
            )
        except ProposalExpectedStateError as exc:
            raise ProposalStateConflictError(str(exc)) from exc

    def _resolve_transition_state(
        self,
        *,
        current_state: ProposalWorkflowState,
        event_type: str,
    ) -> ProposalWorkflowState:
        try:
            return build_transition_state(current_state=current_state, event_type=event_type)
        except ProposalWorkflowRuleError as exc:
            raise ProposalTransitionError(str(exc)) from exc

    def _resolve_approval_transition(
        self,
        *,
        current_state: ProposalWorkflowState,
        approval_type: str,
        approved: bool,
    ) -> tuple[str, ProposalWorkflowState]:
        try:
            return cast(
                tuple[str, ProposalWorkflowState],
                build_approval_transition(
                    current_state=current_state,
                    approval_type=approval_type,
                    approved=approved,
                ),
            )
        except ProposalWorkflowRuleError as exc:
            raise ProposalTransitionError(str(exc)) from exc


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
