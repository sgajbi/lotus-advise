from datetime import datetime
from typing import Optional, Protocol

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)


class DpmRunRepository(Protocol):
    def save_run(self, run: DpmRunRecord) -> None: ...

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]: ...

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]: ...

    def list_runs(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        status: Optional[str],
        portfolio_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmRunRecord], Optional[str]]: ...

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None: ...

    def get_idempotency_mapping(
        self, *, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]: ...

    def append_idempotency_history(self, record: DpmRunIdempotencyHistoryRecord) -> None: ...

    def list_idempotency_history(
        self, *, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]: ...

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None: ...

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None: ...

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]: ...

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]: ...

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int: ...

    def append_workflow_decision(self, decision: DpmRunWorkflowDecisionRecord) -> None: ...

    def list_workflow_decisions(
        self, *, rebalance_run_id: str
    ) -> list[DpmRunWorkflowDecisionRecord]: ...

    def append_lineage_edge(self, edge: DpmLineageEdgeRecord) -> None: ...

    def list_lineage_edges(self, *, entity_id: str) -> list[DpmLineageEdgeRecord]: ...
