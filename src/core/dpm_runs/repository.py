from typing import Optional, Protocol

from src.core.dpm_runs.models import DpmRunIdempotencyRecord, DpmRunRecord


class DpmRunRepository(Protocol):
    def save_run(self, run: DpmRunRecord) -> None: ...

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]: ...

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]: ...

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None: ...

    def get_idempotency_mapping(
        self, *, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]: ...
