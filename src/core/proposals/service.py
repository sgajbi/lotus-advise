import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals.context import (
    ProposalContextResolutionError,
    build_context_resolution_evidence,
    canonicalize_create_request_payload,
    canonicalize_version_request_payload,
    resolve_create_request,
    resolve_version_request,
)
from src.core.proposals.models import (
    ProposalApprovalRecord,
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalApprovalsResponse,
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationRecord,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalCreateResponse,
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
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalVersionLineageItem,
    ProposalVersionRecord,
    ProposalVersionRequest,
    ProposalWorkflowEvent,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.repository import ProposalRepository
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import (
    build_async_operation_replay_response,
    build_proposal_version_replay_response,
)

TERMINAL_STATES = {"EXECUTED", "REJECTED", "CANCELLED", "EXPIRED"}
ASYNC_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED"}
ASYNC_DEFAULT_MAX_ATTEMPTS = 3
ASYNC_OPERATION_LEASE_SECONDS = 60

TRANSITION_MAP: dict[tuple[ProposalWorkflowState, str], ProposalWorkflowState] = {
    ("DRAFT", "SUBMITTED_FOR_RISK_REVIEW"): "RISK_REVIEW",
    ("DRAFT", "SUBMITTED_FOR_COMPLIANCE_REVIEW"): "COMPLIANCE_REVIEW",
    ("RISK_REVIEW", "RISK_APPROVED"): "AWAITING_CLIENT_CONSENT",
    ("RISK_REVIEW", "REJECTED"): "REJECTED",
    ("COMPLIANCE_REVIEW", "COMPLIANCE_APPROVED"): "AWAITING_CLIENT_CONSENT",
    ("COMPLIANCE_REVIEW", "REJECTED"): "REJECTED",
    ("AWAITING_CLIENT_CONSENT", "CLIENT_CONSENT_RECORDED"): "EXECUTION_READY",
    ("AWAITING_CLIENT_CONSENT", "REJECTED"): "REJECTED",
    ("EXECUTION_READY", "EXECUTION_REQUESTED"): "EXECUTION_READY",
    ("EXECUTION_READY", "EXECUTED"): "EXECUTED",
    ("EXECUTION_READY", "EXPIRED"): "EXPIRED",
}

EXECUTION_STATUS_EVENT_TYPES = {
    "EXECUTION_REQUESTED",
    "EXECUTION_ACCEPTED",
    "EXECUTION_PARTIALLY_EXECUTED",
    "EXECUTION_REJECTED",
    "EXECUTION_CANCELLED",
    "EXECUTION_EXPIRED",
    "EXECUTED",
}

EXECUTION_UPDATE_EVENT_MAP: dict[str, tuple[str, ProposalWorkflowState]] = {
    "ACCEPTED": ("EXECUTION_ACCEPTED", "EXECUTION_READY"),
    "PARTIALLY_EXECUTED": ("EXECUTION_PARTIALLY_EXECUTED", "EXECUTION_READY"),
    "REJECTED": ("EXECUTION_REJECTED", "REJECTED"),
    "CANCELLED": ("EXECUTION_CANCELLED", "CANCELLED"),
    "EXPIRED": ("EXECUTION_EXPIRED", "EXPIRED"),
    "EXECUTED": ("EXECUTED", "EXECUTED"),
}


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

    def create_proposal(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
        lifecycle_origin: ProposalLifecycleOrigin = "DIRECT_CREATE",
        source_workspace_id: Optional[str] = None,
        replay_lineage: Optional[dict[str, Any]] = None,
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
        proposal_result = self._run_simulation(
            request=resolved_request.simulate_request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        artifact = build_proposal_artifact(
            request=resolved_request.simulate_request,
            proposal_result=proposal_result,
            created_at=now.isoformat(),
        )
        evidence_bundle = artifact.evidence_bundle.model_dump(mode="json")
        evidence_bundle["context_resolution"] = build_context_resolution_evidence(resolved_request)
        if replay_lineage:
            evidence_bundle["replay_lineage"] = dict(replay_lineage)

        proposal_id = f"pp_{uuid.uuid4().hex[:12]}"
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
        version = self._to_version_record(
            proposal_id=proposal_id,
            version_no=version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=artifact.model_dump(mode="json"),
            evidence_bundle=evidence_bundle,
            created_at=now,
        )
        created_event = ProposalWorkflowEventRecord(
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
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

        return self._to_create_response(
            proposal=proposal, version=version, latest_event=created_event
        )

    def submit_create_proposal_async(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        operation = ProposalAsyncOperationRecord(
            operation_id=f"pop_{uuid.uuid4().hex[:12]}",
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
        return self._to_async_accepted(operation)

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
                replay_lineage=self._build_async_replay_lineage(operation),
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
        return ProposalDetailResponse(
            proposal=self._to_summary(proposal),
            current_version=self._to_version_detail(version, include_evidence=include_evidence),
            last_gate_decision=(
                self._to_version_detail(version, include_evidence=include_evidence).gate_decision
            ),
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
            items=[self._to_summary(row) for row in rows], next_cursor=next_cursor
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        events = self._repository.list_events(proposal_id=proposal_id)
        timeline_events = [self._to_event(event) for event in events]
        return ProposalWorkflowTimelineResponse(
            proposal=self._to_summary(proposal),
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
            self._to_approval(approval)
            for approval in self._repository.list_approvals(proposal_id=proposal_id)
            if approval is not None
        ]
        latest_approval = approvals[-1] if approvals else None
        return ProposalApprovalsResponse(
            proposal=self._to_summary(proposal),
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
            proposal=self._to_summary(proposal),
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
                proposal=self._to_summary(proposal),
                execution_request_id=(
                    str(replay_event.reason_json.get("execution_request_id"))
                    if replay_event.reason_json.get("execution_request_id") is not None
                    else ""
                ),
                handoff_status="REQUESTED",
                execution_provider=str(replay_event.reason_json.get("execution_provider")),
                latest_workflow_event=self._to_event(replay_event),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)
        if proposal.current_state != "EXECUTION_READY":
            raise ProposalStateConflictError(
                "STATE_CONFLICT: proposal must be EXECUTION_READY for execution handoff"
            )

        occurred_at = _utc_now()
        execution_request_id = payload.external_request_id or f"pex_{uuid.uuid4().hex[:12]}"
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
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
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
            proposal=self._to_summary(result.proposal),
            execution_request_id=execution_request_id,
            handoff_status="REQUESTED",
            execution_provider=payload.execution_provider,
            latest_workflow_event=self._to_event(result.event),
        )

    def get_execution_status(self, *, proposal_id: str) -> ProposalExecutionStatusResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        events = self._repository.list_events(proposal_id=proposal_id)
        latest_execution_requested = self._latest_execution_requested_event(events)
        latest_execution_event = self._latest_execution_status_event(events)

        handoff_status = "NOT_REQUESTED"
        execution_request_id: str | None = None
        execution_provider: str | None = None
        related_version_no: int | None = None
        handoff_requested_at: str | None = None
        executed_at: str | None = None
        external_execution_id: str | None = None
        if latest_execution_requested is not None:
            handoff_status = "REQUESTED"
            execution_request_id = latest_execution_requested.reason_json.get(
                "execution_request_id"
            )
            execution_provider = latest_execution_requested.reason_json.get("execution_provider")
            related_version_no = latest_execution_requested.related_version_no
            handoff_requested_at = latest_execution_requested.occurred_at.isoformat()

        if latest_execution_event is not None:
            handoff_status = self._execution_status_for_event(latest_execution_event.event_type)
            if latest_execution_event.event_type == "EXECUTED":
                executed_at = latest_execution_event.occurred_at.isoformat()
            external_execution_id = (
                latest_execution_event.reason_json.get("external_execution_id")
                or latest_execution_event.reason_json.get("execution_id")
            )
            related_version_no = latest_execution_event.related_version_no or related_version_no
            if latest_execution_requested is None:
                execution_request_id = latest_execution_event.reason_json.get(
                    "execution_request_id"
                )
                execution_provider = latest_execution_event.reason_json.get("execution_provider")

        return ProposalExecutionStatusResponse(
            proposal=self._to_summary(proposal),
            handoff_status=handoff_status,
            execution_request_id=execution_request_id,
            execution_provider=execution_provider,
            related_version_no=related_version_no,
            handoff_requested_at=handoff_requested_at,
            executed_at=executed_at,
            external_execution_id=external_execution_id,
            latest_workflow_event=(
                self._to_event(latest_execution_event)
                if latest_execution_event is not None
                else None
            ),
            explanation={
                "source": "ADVISORY_WORKFLOW_EVENTS",
                "state_correlation": self._execution_state_correlation(
                    handoff_status=handoff_status
                ),
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
        latest_execution_requested = self._latest_execution_requested_event(events)
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

        event_type, to_state = EXECUTION_UPDATE_EVENT_MAP[payload.update_status]
        if proposal.current_state in TERMINAL_STATES:
            raise ProposalStateConflictError("PROPOSAL_TERMINAL_STATE: execution update rejected")

        occurred_at = (
            datetime.fromisoformat(payload.occurred_at)
            if payload.occurred_at is not None
            else _utc_now()
        )
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
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            event_type=event_type,
            from_state=proposal.current_state,
            to_state=to_state,
            actor_id=payload.actor_id,
            occurred_at=occurred_at,
            reason_json={k: v for k, v in reason_json.items() if v is not None},
            related_version_no=(
                payload.related_version_no
                or latest_execution_requested.related_version_no
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
        return self._to_async_status(operation)

    def get_async_operation_replay(
        self, *, operation_id: str
    ) -> AdvisoryReplayEvidenceResponse:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")

        proposal = None
        version = None
        if operation.proposal_id is not None:
            proposal = self._repository.get_proposal(proposal_id=operation.proposal_id)
            if proposal is not None:
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
        return build_async_operation_replay_response(
            operation=operation,
            proposal=proposal,
            version=version,
        )

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> ProposalAsyncOperationStatusResponse:
        operation = self._repository.get_operation_by_correlation(correlation_id=correlation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return self._to_async_status(operation)

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
        return self._to_version_detail(version, include_evidence=include_evidence)

    def create_version(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
        replay_lineage: Optional[dict[str, Any]] = None,
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
            request_hash=request_hash,
            idempotency_key=None,
            correlation_id=correlation_id,
        )
        artifact = build_proposal_artifact(
            request=resolved_request.simulate_request,
            proposal_result=proposal_result,
            created_at=now.isoformat(),
        )
        evidence_bundle = artifact.evidence_bundle.model_dump(mode="json")
        evidence_bundle["context_resolution"] = build_context_resolution_evidence(resolved_request)
        if replay_lineage:
            evidence_bundle["replay_lineage"] = dict(replay_lineage)

        next_version_no = proposal.current_version_no + 1
        version = self._to_version_record(
            proposal_id=proposal.proposal_id,
            version_no=next_version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=artifact.model_dump(mode="json"),
            evidence_bundle=evidence_bundle,
            created_at=now,
        )
        event = ProposalWorkflowEventRecord(
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal.proposal_id,
            event_type="NEW_VERSION_CREATED",
            from_state=proposal.current_state,
            to_state=proposal.current_state,
            actor_id=payload.created_by,
            occurred_at=now,
            reason_json={"correlation_id": correlation_id} if correlation_id else {},
            related_version_no=next_version_no,
        )

        proposal.current_version_no = next_version_no
        proposal.last_event_at = now
        self._repository.create_version(version)
        self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return self._to_create_response(proposal=proposal, version=version, latest_event=event)

    def submit_create_version_async(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        operation = ProposalAsyncOperationRecord(
            operation_id=f"pop_{uuid.uuid4().hex[:12]}",
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
        return self._to_async_accepted(operation)

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
                replay_lineage=self._build_async_replay_lineage(operation),
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
                latest_workflow_event=self._to_event(replay_event),
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
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
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
            latest_workflow_event=self._to_event(result.event),
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
                latest_workflow_event=self._to_event(replay_event),
                approval=self._to_approval(replay_approval),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)

        details_json = dict(payload.details)
        if idempotency_key:
            details_json["idempotency_key"] = idempotency_key
            details_json["idempotency_request_hash"] = request_hash
        approval = ProposalApprovalRecordData(
            approval_id=f"pap_{uuid.uuid4().hex[:12]}",
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
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
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
            latest_workflow_event=self._to_event(result.event),
            approval=self._to_approval(result.approval),
        )

    def _get_replayed_event(
        self, *, proposal_id: str, idempotency_key: Optional[str], request_hash: str
    ) -> Optional[ProposalWorkflowEventRecord]:
        if not idempotency_key:
            return None
        for event in reversed(self._repository.list_events(proposal_id=proposal_id)):
            existing_key = event.reason_json.get("idempotency_key")
            if existing_key != idempotency_key:
                continue
            existing_hash = event.reason_json.get("idempotency_request_hash")
            if existing_hash is not None and existing_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return event
        return None

    def _get_replayed_approval(
        self, *, proposal_id: str, idempotency_key: Optional[str], request_hash: str
    ) -> Optional[ProposalApprovalRecordData]:
        if not idempotency_key:
            return None
        for approval in reversed(self._repository.list_approvals(proposal_id=proposal_id)):
            existing_key = approval.details_json.get("idempotency_key")
            if existing_key != idempotency_key:
                continue
            existing_hash = approval.details_json.get("idempotency_request_hash")
            if existing_hash is not None and existing_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return approval
        return None

    def _read_create_response(self, *, proposal_id: str, version_no: int) -> ProposalCreateResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
        events = self._repository.list_events(proposal_id=proposal_id)
        if proposal is None or version is None or not events:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
        return self._to_create_response(proposal=proposal, version=version, latest_event=events[-1])

    def _to_create_response(
        self,
        *,
        proposal: ProposalRecord,
        version: ProposalVersionRecord,
        latest_event: ProposalWorkflowEventRecord,
    ) -> ProposalCreateResponse:
        return ProposalCreateResponse(
            proposal=self._to_summary(proposal),
            version=self._to_version_detail(version, include_evidence=True),
            latest_workflow_event=self._to_event(latest_event),
        )

    def _to_summary(self, proposal: ProposalRecord) -> ProposalSummary:
        return ProposalSummary(
            proposal_id=proposal.proposal_id,
            portfolio_id=proposal.portfolio_id,
            mandate_id=proposal.mandate_id,
            jurisdiction=proposal.jurisdiction,
            created_by=proposal.created_by,
            created_at=proposal.created_at.isoformat(),
            last_event_at=proposal.last_event_at.isoformat(),
            current_state=proposal.current_state,
            current_version_no=proposal.current_version_no,
            title=proposal.title,
            lifecycle_origin=proposal.lifecycle_origin,
            source_workspace_id=proposal.source_workspace_id,
        )

    def _validate_lifecycle_origin(
        self,
        *,
        lifecycle_origin: ProposalLifecycleOrigin,
        source_workspace_id: Optional[str],
    ) -> None:
        if lifecycle_origin == "WORKSPACE_HANDOFF" and not source_workspace_id:
            raise ProposalValidationError("WORKSPACE_HANDOFF_SOURCE_WORKSPACE_ID_REQUIRED")
        if lifecycle_origin == "DIRECT_CREATE" and source_workspace_id is not None:
            raise ProposalValidationError("DIRECT_CREATE_CANNOT_INCLUDE_SOURCE_WORKSPACE_ID")

    def _to_version_detail(
        self, version: ProposalVersionRecord, *, include_evidence: bool
    ) -> ProposalVersionDetail:
        evidence_bundle_json: dict[str, Any] = (
            version.evidence_bundle_json if include_evidence else {}
        )
        return ProposalVersionDetail(
            proposal_version_id=version.proposal_version_id,
            proposal_id=version.proposal_id,
            version_no=version.version_no,
            created_at=version.created_at.isoformat(),
            request_hash=version.request_hash,
            artifact_hash=version.artifact_hash,
            simulation_hash=version.simulation_hash,
            status_at_creation=version.status_at_creation,
            proposal_result=version.proposal_result_json,
            artifact=version.artifact_json,
            evidence_bundle=evidence_bundle_json,
            gate_decision=version.gate_decision_json,
        )

    def _to_event(self, event: ProposalWorkflowEventRecord) -> ProposalWorkflowEvent:
        return ProposalWorkflowEvent(
            event_id=event.event_id,
            proposal_id=event.proposal_id,
            event_type=event.event_type,
            from_state=event.from_state,
            to_state=event.to_state,
            actor_id=event.actor_id,
            occurred_at=event.occurred_at.isoformat(),
            reason=event.reason_json,
            related_version_no=event.related_version_no,
        )

    def _to_approval(
        self, approval: Optional[ProposalApprovalRecordData]
    ) -> Optional[ProposalApprovalRecord]:
        if approval is None:
            return None
        return ProposalApprovalRecord(
            approval_id=approval.approval_id,
            proposal_id=approval.proposal_id,
            approval_type=approval.approval_type,
            approved=approval.approved,
            actor_id=approval.actor_id,
            occurred_at=approval.occurred_at.isoformat(),
            details=approval.details_json,
            related_version_no=approval.related_version_no,
        )

    def _to_version_record(
        self,
        *,
        proposal_id: str,
        version_no: int,
        request_hash: str,
        proposal_result: ProposalResult,
        artifact: dict[str, Any],
        evidence_bundle: dict[str, Any],
        created_at: datetime,
    ) -> ProposalVersionRecord:
        simulation_payload = proposal_result.model_dump(mode="json")
        simulation_hash_payload = strip_keys(
            simulation_payload,
            exclude={"correlation_id", "idempotency_key"},
        )
        simulation_hash = hash_canonical_payload(simulation_hash_payload)
        artifact_hash = artifact["evidence_bundle"]["hashes"]["artifact_hash"]
        return ProposalVersionRecord(
            proposal_version_id=f"ppv_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            version_no=version_no,
            created_at=created_at,
            request_hash=request_hash,
            artifact_hash=artifact_hash,
            simulation_hash=simulation_hash,
            status_at_creation=proposal_result.status,
            proposal_result_json=simulation_payload,
            artifact_json=artifact,
            evidence_bundle_json=evidence_bundle if self._store_evidence_bundle else {},
            gate_decision_json=(
                proposal_result.gate_decision.model_dump(mode="json")
                if proposal_result.gate_decision is not None
                else None
            ),
        )

    def _to_async_accepted(
        self, operation: ProposalAsyncOperationRecord
    ) -> ProposalAsyncAcceptedResponse:
        return ProposalAsyncAcceptedResponse(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            status=operation.status,
            correlation_id=operation.correlation_id,
            created_at=operation.created_at.isoformat(),
            attempt_count=operation.attempt_count,
            max_attempts=operation.max_attempts,
            status_url=f"/advisory/proposals/operations/{operation.operation_id}",
        )

    def _to_async_status(
        self, operation: ProposalAsyncOperationRecord
    ) -> ProposalAsyncOperationStatusResponse:
        return ProposalAsyncOperationStatusResponse(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            status=operation.status,
            correlation_id=operation.correlation_id,
            idempotency_key=operation.idempotency_key,
            proposal_id=operation.proposal_id,
            created_by=operation.created_by,
            created_at=operation.created_at.isoformat(),
            started_at=(operation.started_at.isoformat() if operation.started_at else None),
            finished_at=(operation.finished_at.isoformat() if operation.finished_at else None),
            attempt_count=operation.attempt_count,
            max_attempts=operation.max_attempts,
            lease_expires_at=(
                operation.lease_expires_at.isoformat() if operation.lease_expires_at else None
            ),
            result=(
                ProposalCreateResponse.model_validate(operation.result_json)
                if operation.result_json is not None
                else None
            ),
            error=operation.error_json,
        )

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
        return build_proposal_version_replay_response(proposal=proposal, version=version)

    def _resolve_create_async_payload(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        fallback_payload: Optional[ProposalCreateRequest],
        fallback_idempotency_key: Optional[str],
    ) -> tuple[ProposalCreateRequest, str] | None:
        payload_json = operation.payload_json.get("payload")
        if not isinstance(payload_json, dict):
            if fallback_payload is None:
                self._mark_operation_failed(
                    operation=operation,
                    code="ProposalLifecycleError",
                    message="PROPOSAL_ASYNC_PAYLOAD_INVALID",
                )
                return None
            payload = fallback_payload
        else:
            try:
                payload = ProposalCreateRequest.model_validate(payload_json)
            except Exception:
                self._mark_operation_failed(
                    operation=operation,
                    code="ProposalLifecycleError",
                    message="PROPOSAL_ASYNC_PAYLOAD_INVALID",
                )
                return None

        resolved_idempotency_key = (
            operation.payload_json.get("idempotency_key")
            or operation.idempotency_key
            or fallback_idempotency_key
        )
        if not isinstance(resolved_idempotency_key, str) or not resolved_idempotency_key:
            self._mark_operation_failed(
                operation=operation,
                code="ProposalLifecycleError",
                message="PROPOSAL_ASYNC_IDEMPOTENCY_KEY_REQUIRED",
            )
            return None
        return payload, resolved_idempotency_key

    def _resolve_version_async_payload(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        fallback_proposal_id: Optional[str],
        fallback_payload: Optional[ProposalVersionRequest],
    ) -> tuple[str, ProposalVersionRequest] | None:
        payload_json = operation.payload_json.get("payload")
        if not isinstance(payload_json, dict):
            if fallback_payload is None:
                self._mark_operation_failed(
                    operation=operation,
                    code="ProposalLifecycleError",
                    message="PROPOSAL_ASYNC_PAYLOAD_INVALID",
                )
                return None
            payload = fallback_payload
        else:
            try:
                payload = ProposalVersionRequest.model_validate(payload_json)
            except Exception:
                self._mark_operation_failed(
                    operation=operation,
                    code="ProposalLifecycleError",
                    message="PROPOSAL_ASYNC_PAYLOAD_INVALID",
                )
                return None

        resolved_proposal_id = operation.payload_json.get("proposal_id") or operation.proposal_id
        if not isinstance(resolved_proposal_id, str) or not resolved_proposal_id:
            resolved_proposal_id = fallback_proposal_id or ""
        if not resolved_proposal_id:
            self._mark_operation_failed(
                operation=operation,
                code="ProposalLifecycleError",
                message="PROPOSAL_ASYNC_PROPOSAL_ID_REQUIRED",
            )
            return None
        return resolved_proposal_id, payload

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
        attempt_started_at = _utc_now()
        operation.status = "RUNNING"
        operation.attempt_count += 1
        operation.started_at = attempt_started_at
        operation.lease_expires_at = _utc_after(seconds=ASYNC_OPERATION_LEASE_SECONDS)
        operation.finished_at = None
        operation.result_json = None
        operation.error_json = None
        self._repository.update_operation(operation)

    def _mark_operation_succeeded(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        response: ProposalCreateResponse,
    ) -> None:
        operation.status = "SUCCEEDED"
        operation.proposal_id = response.proposal.proposal_id
        operation.result_json = response.model_dump(mode="json")
        operation.error_json = None
        operation.lease_expires_at = None
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def _mark_operation_failed(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        code: str,
        message: str,
    ) -> None:
        operation.status = "FAILED"
        operation.result_json = None
        operation.error_json = {"code": code, "message": message}
        operation.lease_expires_at = None
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def _requeue_or_fail_runtime_exception(
        self,
        *,
        operation: ProposalAsyncOperationRecord,
        exc: Exception,
    ) -> bool:
        operation.result_json = None
        operation.lease_expires_at = None
        operation.error_json = {
            "code": type(exc).__name__,
            "message": str(exc) or type(exc).__name__,
        }
        if operation.attempt_count < operation.max_attempts:
            operation.status = "PENDING"
            operation.finished_at = None
            self._repository.update_operation(operation)
            return True

        operation.status = "FAILED"
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)
        return False

    def _build_async_replay_lineage(
        self,
        operation: ProposalAsyncOperationRecord,
    ) -> dict[str, Any]:
        return {
            "async_operation_id": operation.operation_id,
            "async_operation_type": operation.operation_type,
            "correlation_id": operation.correlation_id,
            "idempotency_key": operation.idempotency_key,
        }

    def _run_simulation(
        self,
        *,
        request: ProposalSimulateRequest,
        request_hash: str,
        idempotency_key: Optional[str],
        correlation_id: Optional[str],
    ) -> ProposalResult:
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        return evaluate_advisory_proposal(
            request=request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=resolved_correlation_id,
        )

    def _validate_simulation_flag(self, request: ProposalSimulateRequest) -> None:
        if (
            self._require_proposal_simulation_flag
            and not request.options.enable_proposal_simulation
        ):
            raise ProposalValidationError(
                "PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true"
            )

    def _validate_expected_state(
        self,
        current_state: ProposalWorkflowState,
        expected_state: Optional[ProposalWorkflowState],
    ) -> None:
        if expected_state is None and self._require_expected_state:
            raise ProposalStateConflictError("STATE_CONFLICT: expected_state is required")
        if expected_state is not None and expected_state != current_state:
            raise ProposalStateConflictError("STATE_CONFLICT: expected_state mismatch")

    def _resolve_transition_state(
        self,
        *,
        current_state: ProposalWorkflowState,
        event_type: str,
    ) -> ProposalWorkflowState:
        if event_type == "CANCELLED" and current_state not in TERMINAL_STATES:
            return "CANCELLED"
        next_state = TRANSITION_MAP.get((current_state, event_type))
        if next_state is None:
            raise ProposalTransitionError("INVALID_TRANSITION")
        return next_state

    def _resolve_approval_transition(
        self,
        *,
        current_state: ProposalWorkflowState,
        approval_type: str,
        approved: bool,
    ) -> tuple[str, ProposalWorkflowState]:
        if approval_type == "RISK":
            if current_state != "RISK_REVIEW":
                raise ProposalTransitionError("INVALID_APPROVAL_STATE")
            return (
                "RISK_APPROVED" if approved else "REJECTED",
                "AWAITING_CLIENT_CONSENT" if approved else "REJECTED",
            )

        if approval_type == "COMPLIANCE":
            if current_state != "COMPLIANCE_REVIEW":
                raise ProposalTransitionError("INVALID_APPROVAL_STATE")
            return (
                "COMPLIANCE_APPROVED" if approved else "REJECTED",
                "AWAITING_CLIENT_CONSENT" if approved else "REJECTED",
            )

        if approval_type == "CLIENT_CONSENT":
            if current_state != "AWAITING_CLIENT_CONSENT":
                raise ProposalTransitionError("INVALID_APPROVAL_STATE")
            return (
                "CLIENT_CONSENT_RECORDED" if approved else "REJECTED",
                "EXECUTION_READY" if approved else "REJECTED",
            )

        raise ProposalTransitionError("INVALID_APPROVAL_TYPE")

    def _latest_execution_requested_event(
        self, events: list[ProposalWorkflowEventRecord]
    ) -> ProposalWorkflowEventRecord | None:
        for event in reversed(events):
            if event.event_type == "EXECUTION_REQUESTED":
                return event
        return None

    def _latest_execution_status_event(
        self, events: list[ProposalWorkflowEventRecord]
    ) -> ProposalWorkflowEventRecord | None:
        for event in reversed(events):
            if event.event_type in EXECUTION_STATUS_EVENT_TYPES:
                return event
        return None

    def _execution_status_for_event(self, event_type: str) -> str:
        mapping = {
            "EXECUTION_REQUESTED": "REQUESTED",
            "EXECUTION_ACCEPTED": "ACCEPTED",
            "EXECUTION_PARTIALLY_EXECUTED": "PARTIALLY_EXECUTED",
            "EXECUTION_REJECTED": "REJECTED",
            "EXECUTION_CANCELLED": "CANCELLED",
            "EXECUTION_EXPIRED": "EXPIRED",
            "EXECUTED": "EXECUTED",
        }
        return mapping.get(event_type, "NOT_REQUESTED")

    def _execution_state_correlation(self, *, handoff_status: str) -> str:
        mapping = {
            "REQUESTED": "EXECUTION_REQUESTED_EVENT",
            "ACCEPTED": "EXECUTION_REQUESTED_AND_ACCEPTED_EVENTS",
            "PARTIALLY_EXECUTED": "EXECUTION_REQUESTED_AND_PARTIAL_EXECUTION_EVENTS",
            "EXECUTED": "EXECUTION_REQUESTED_AND_EXECUTED_EVENTS",
            "REJECTED": "EXECUTION_REQUESTED_AND_REJECTED_EVENTS",
            "CANCELLED": "EXECUTION_REQUESTED_AND_CANCELLED_EVENTS",
            "EXPIRED": "EXECUTION_REQUESTED_AND_EXPIRED_EVENTS",
        }
        return mapping.get(handoff_status, "NO_EXECUTION_EVENTS_RECORDED")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_after(*, seconds: int) -> datetime:
    return _utc_now().replace(microsecond=0) + timedelta(seconds=seconds)
