from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.core.dpm_runs.repository import DpmRunRepository


class InMemoryDpmRunRepository(DpmRunRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, DpmRunRecord] = {}
        self._run_id_by_correlation: dict[str, str] = {}
        self._idempotency: dict[str, DpmRunIdempotencyRecord] = {}
        self._operations: dict[str, DpmAsyncOperationRecord] = {}
        self._operation_by_correlation: dict[str, str] = {}
        self._workflow_decisions: dict[str, list[DpmRunWorkflowDecisionRecord]] = {}

    def save_run(self, run: DpmRunRecord) -> None:
        with self._lock:
            self._runs[run.rebalance_run_id] = deepcopy(run)
            self._run_id_by_correlation[run.correlation_id] = run.rebalance_run_id

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]:
        with self._lock:
            run = self._runs.get(rebalance_run_id)
            return deepcopy(run) if run is not None else None

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]:
        with self._lock:
            run_id = self._run_id_by_correlation.get(correlation_id)
            if run_id is None:
                return None
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None:
        with self._lock:
            self._idempotency[record.idempotency_key] = deepcopy(record)

    def get_idempotency_mapping(self, *, idempotency_key: str) -> Optional[DpmRunIdempotencyRecord]:
        with self._lock:
            record = self._idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None:
        with self._lock:
            self._operations[operation.operation_id] = deepcopy(operation)
            self._operation_by_correlation[operation.correlation_id] = operation.operation_id

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        with self._lock:
            operation_id = self._operation_by_correlation.get(correlation_id)
            if operation_id is None:
                return None
            operation = self._operations.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int:
        with self._lock:
            cutoff = now.astimezone(timezone.utc) - timedelta(seconds=ttl_seconds)
            removed = 0
            for operation_id, operation in list(self._operations.items()):
                anchor = operation.finished_at or operation.created_at
                if anchor < cutoff:
                    self._operations.pop(operation_id, None)
                    if self._operation_by_correlation.get(operation.correlation_id) == operation_id:
                        self._operation_by_correlation.pop(operation.correlation_id, None)
                    removed += 1
            return removed

    def append_workflow_decision(self, decision: DpmRunWorkflowDecisionRecord) -> None:
        with self._lock:
            decisions = self._workflow_decisions.setdefault(decision.run_id, [])
            decisions.append(deepcopy(decision))

    def list_workflow_decisions(
        self, *, rebalance_run_id: str
    ) -> list[DpmRunWorkflowDecisionRecord]:
        with self._lock:
            decisions = self._workflow_decisions.get(rebalance_run_id, [])
            return [deepcopy(decision) for decision in decisions]
