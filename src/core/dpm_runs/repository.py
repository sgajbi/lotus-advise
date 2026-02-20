from datetime import datetime
from typing import Optional, Protocol

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
)


class DpmRunRepository(Protocol):
    def save_run(self, run: DpmRunRecord) -> None: ...

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]: ...

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]: ...

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None: ...

    def get_idempotency_mapping(
        self, *, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]: ...

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None: ...

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None: ...

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]: ...

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]: ...

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int: ...
