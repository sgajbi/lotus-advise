import uuid
from datetime import datetime, timezone
from typing import Optional

from src.core.dpm_runs.artifact import build_dpm_run_artifact
from src.core.dpm_runs.models import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationRecord,
    DpmAsyncOperationStatusResponse,
    DpmRunArtifactResponse,
    DpmRunIdempotencyLookupResponse,
    DpmRunIdempotencyRecord,
    DpmRunLookupResponse,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmRunWorkflowDecisionResponse,
    DpmRunWorkflowHistoryResponse,
    DpmRunWorkflowResponse,
    DpmWorkflowActionType,
    DpmWorkflowStatus,
)
from src.core.dpm_runs.repository import DpmRunRepository
from src.core.models import RebalanceResult


class DpmRunNotFoundError(Exception):
    pass


class DpmWorkflowDisabledError(Exception):
    pass


class DpmWorkflowTransitionError(Exception):
    pass


class DpmRunSupportService:
    def __init__(
        self,
        *,
        repository: DpmRunRepository,
        async_operation_ttl_seconds: int = 86400,
        workflow_enabled: bool = False,
        workflow_requires_review_for_statuses: Optional[set[str]] = None,
    ) -> None:
        self._repository = repository
        self._async_operation_ttl_seconds = max(1, async_operation_ttl_seconds)
        self._workflow_enabled = workflow_enabled
        self._workflow_requires_review_for_statuses = {
            value.strip()
            for value in (workflow_requires_review_for_statuses or {"PENDING_REVIEW"})
            if value.strip()
        }

    def record_run(
        self,
        *,
        result: RebalanceResult,
        request_hash: str,
        portfolio_id: str,
        idempotency_key: Optional[str],
        created_at: Optional[datetime] = None,
    ) -> None:
        now = created_at or datetime.now(timezone.utc)
        run = DpmRunRecord(
            rebalance_run_id=result.rebalance_run_id,
            correlation_id=result.correlation_id,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            portfolio_id=portfolio_id,
            created_at=now,
            result_json=result.model_dump(mode="json"),
        )
        self._repository.save_run(run)
        if idempotency_key is not None:
            self._repository.save_idempotency_mapping(
                DpmRunIdempotencyRecord(
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    rebalance_run_id=result.rebalance_run_id,
                    created_at=now,
                )
            )

    def get_run(self, *, rebalance_run_id: str) -> DpmRunLookupResponse:
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return self._to_lookup_response(run)

    def get_run_by_correlation(self, *, correlation_id: str) -> DpmRunLookupResponse:
        run = self._repository.get_run_by_correlation(correlation_id=correlation_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return self._to_lookup_response(run)

    def get_idempotency_lookup(self, *, idempotency_key: str) -> DpmRunIdempotencyLookupResponse:
        record = self._repository.get_idempotency_mapping(idempotency_key=idempotency_key)
        if record is None:
            raise DpmRunNotFoundError("DPM_IDEMPOTENCY_KEY_NOT_FOUND")
        return DpmRunIdempotencyLookupResponse(
            idempotency_key=record.idempotency_key,
            request_hash=record.request_hash,
            rebalance_run_id=record.rebalance_run_id,
            created_at=record.created_at.isoformat(),
        )

    def get_run_artifact(self, *, rebalance_run_id: str) -> DpmRunArtifactResponse:
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        return build_dpm_run_artifact(run=run)

    def submit_analyze_async(
        self,
        *,
        correlation_id: Optional[str],
        request_json: dict,
        created_at: Optional[datetime] = None,
    ) -> DpmAsyncAcceptedResponse:
        self._cleanup_expired_operations()
        now = created_at or _utc_now()
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        operation = DpmAsyncOperationRecord(
            operation_id=f"dop_{uuid.uuid4().hex[:12]}",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id=resolved_correlation_id,
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json=request_json,
        )
        self._repository.create_operation(operation)
        return self._to_async_accepted(operation)

    def mark_operation_running(self, *, operation_id: str) -> None:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        operation.status = "RUNNING"
        operation.started_at = _utc_now()
        self._repository.update_operation(operation)

    def complete_operation_success(self, *, operation_id: str, result_json: dict) -> None:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        operation.status = "SUCCEEDED"
        operation.result_json = result_json
        operation.error_json = None
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def complete_operation_failure(self, *, operation_id: str, code: str, message: str) -> None:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        operation.status = "FAILED"
        operation.result_json = None
        operation.error_json = {"code": code, "message": message}
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def get_async_operation(self, *, operation_id: str) -> DpmAsyncOperationStatusResponse:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        return self._to_async_status(operation)

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> DpmAsyncOperationStatusResponse:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation_by_correlation(correlation_id=correlation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        return self._to_async_status(operation)

    def prepare_analyze_operation_execution(self, *, operation_id: str) -> tuple[dict, str]:
        self._cleanup_expired_operations()
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")
        if operation.status != "PENDING" or operation.request_json is None:
            raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_EXECUTABLE")
        operation.status = "RUNNING"
        operation.started_at = _utc_now()
        self._repository.update_operation(operation)
        return operation.request_json, operation.correlation_id

    def get_workflow(self, *, rebalance_run_id: str) -> DpmRunWorkflowResponse:
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        latest_decision = self._latest_workflow_decision(rebalance_run_id=rebalance_run_id)
        workflow_status = self._resolve_workflow_status(
            run_status=str(run.result_json.get("status", "")),
            latest_decision=latest_decision,
        )
        return DpmRunWorkflowResponse(
            run_id=run.rebalance_run_id,
            run_status=str(run.result_json.get("status", "")),
            workflow_status=workflow_status,
            requires_review=self._workflow_required_for_run_status(
                run_status=str(run.result_json.get("status", ""))
            ),
            latest_decision=(
                self._to_workflow_decision_response(latest_decision)
                if latest_decision is not None
                else None
            ),
        )

    def get_workflow_history(self, *, rebalance_run_id: str) -> DpmRunWorkflowHistoryResponse:
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        decisions = self._repository.list_workflow_decisions(rebalance_run_id=rebalance_run_id)
        decisions = sorted(decisions, key=lambda item: item.decided_at)
        return DpmRunWorkflowHistoryResponse(
            run_id=rebalance_run_id,
            decisions=[self._to_workflow_decision_response(decision) for decision in decisions],
        )

    def apply_workflow_action(
        self,
        *,
        rebalance_run_id: str,
        action: DpmWorkflowActionType,
        reason_code: str,
        comment: Optional[str],
        actor_id: str,
        correlation_id: str,
    ) -> DpmRunWorkflowResponse:
        if not self._workflow_enabled:
            raise DpmWorkflowDisabledError("DPM_WORKFLOW_DISABLED")
        run = self._repository.get_run(rebalance_run_id=rebalance_run_id)
        if run is None:
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")
        run_status = str(run.result_json.get("status", ""))
        if not self._workflow_required_for_run_status(run_status=run_status):
            raise DpmWorkflowTransitionError("DPM_WORKFLOW_NOT_REQUIRED_FOR_RUN_STATUS")

        latest_decision = self._latest_workflow_decision(rebalance_run_id=rebalance_run_id)
        current_status = self._resolve_workflow_status(
            run_status=run_status,
            latest_decision=latest_decision,
        )
        next_status = _resolve_workflow_transition(current_status=current_status, action=action)
        if next_status is None:
            raise DpmWorkflowTransitionError("DPM_WORKFLOW_INVALID_TRANSITION")

        decision = DpmRunWorkflowDecisionRecord(
            decision_id=f"dwd_{uuid.uuid4().hex[:12]}",
            run_id=rebalance_run_id,
            action=action,
            reason_code=reason_code,
            comment=comment,
            actor_id=actor_id,
            decided_at=_utc_now(),
            correlation_id=correlation_id,
        )
        self._repository.append_workflow_decision(decision)
        return DpmRunWorkflowResponse(
            run_id=rebalance_run_id,
            run_status=run_status,
            workflow_status=next_status,
            requires_review=True,
            latest_decision=self._to_workflow_decision_response(decision),
        )

    def _to_lookup_response(self, run: DpmRunRecord) -> DpmRunLookupResponse:
        return DpmRunLookupResponse(
            rebalance_run_id=run.rebalance_run_id,
            correlation_id=run.correlation_id,
            request_hash=run.request_hash,
            idempotency_key=run.idempotency_key,
            portfolio_id=run.portfolio_id,
            created_at=run.created_at.isoformat(),
            result=RebalanceResult.model_validate(run.result_json),
        )

    def _to_async_accepted(self, operation: DpmAsyncOperationRecord) -> DpmAsyncAcceptedResponse:
        return DpmAsyncAcceptedResponse(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            status=operation.status,
            correlation_id=operation.correlation_id,
            created_at=operation.created_at.isoformat(),
            status_url=f"/rebalance/operations/{operation.operation_id}",
            execute_url=f"/rebalance/operations/{operation.operation_id}/execute",
        )

    def _to_async_status(
        self, operation: DpmAsyncOperationRecord
    ) -> DpmAsyncOperationStatusResponse:
        return DpmAsyncOperationStatusResponse(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            status=operation.status,
            is_executable=(operation.status == "PENDING" and operation.request_json is not None),
            correlation_id=operation.correlation_id,
            created_at=operation.created_at.isoformat(),
            started_at=(operation.started_at.isoformat() if operation.started_at else None),
            finished_at=(operation.finished_at.isoformat() if operation.finished_at else None),
            result=operation.result_json,
            error=operation.error_json,
        )

    def _cleanup_expired_operations(self) -> None:
        self._repository.purge_expired_operations(
            ttl_seconds=self._async_operation_ttl_seconds,
            now=_utc_now(),
        )

    def _latest_workflow_decision(
        self, *, rebalance_run_id: str
    ) -> Optional[DpmRunWorkflowDecisionRecord]:
        decisions = self._repository.list_workflow_decisions(rebalance_run_id=rebalance_run_id)
        if not decisions:
            return None
        return max(decisions, key=lambda item: item.decided_at)

    def _workflow_required_for_run_status(self, *, run_status: str) -> bool:
        return self._workflow_enabled and run_status in self._workflow_requires_review_for_statuses

    def _resolve_workflow_status(
        self,
        *,
        run_status: str,
        latest_decision: Optional[DpmRunWorkflowDecisionRecord],
    ) -> DpmWorkflowStatus:
        if not self._workflow_required_for_run_status(run_status=run_status):
            return "NOT_REQUIRED"
        if latest_decision is None:
            return "PENDING_REVIEW"
        return _status_for_action(latest_decision.action)

    def _to_workflow_decision_response(
        self, decision: DpmRunWorkflowDecisionRecord
    ) -> DpmRunWorkflowDecisionResponse:
        return DpmRunWorkflowDecisionResponse(
            decision_id=decision.decision_id,
            run_id=decision.run_id,
            action=decision.action,
            reason_code=decision.reason_code,
            comment=decision.comment,
            actor_id=decision.actor_id,
            decided_at=decision.decided_at.isoformat(),
            correlation_id=decision.correlation_id,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _status_for_action(action: DpmWorkflowActionType) -> DpmWorkflowStatus:
    if action == "APPROVE":
        return "APPROVED"
    if action == "REJECT":
        return "REJECTED"
    return "PENDING_REVIEW"


_VALID_WORKFLOW_TRANSITIONS: dict[
    tuple[DpmWorkflowStatus, DpmWorkflowActionType], DpmWorkflowStatus
] = {
    ("PENDING_REVIEW", "APPROVE"): "APPROVED",
    ("PENDING_REVIEW", "REJECT"): "REJECTED",
    ("PENDING_REVIEW", "REQUEST_CHANGES"): "PENDING_REVIEW",
    ("APPROVED", "REQUEST_CHANGES"): "PENDING_REVIEW",
    ("APPROVED", "REJECT"): "REJECTED",
    ("REJECTED", "REQUEST_CHANGES"): "PENDING_REVIEW",
}


def _resolve_workflow_transition(
    *, current_status: DpmWorkflowStatus, action: DpmWorkflowActionType
) -> Optional[DpmWorkflowStatus]:
    return _VALID_WORKFLOW_TRANSITIONS.get((current_status, action))
