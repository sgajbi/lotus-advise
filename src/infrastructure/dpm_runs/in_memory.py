from copy import deepcopy
from threading import Lock
from typing import Optional

from src.core.dpm_runs.models import DpmRunIdempotencyRecord, DpmRunRecord
from src.core.dpm_runs.repository import DpmRunRepository


class InMemoryDpmRunRepository(DpmRunRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, DpmRunRecord] = {}
        self._run_id_by_correlation: dict[str, str] = {}
        self._idempotency: dict[str, DpmRunIdempotencyRecord] = {}

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

    def get_idempotency_mapping(
        self, *, idempotency_key: str
    ) -> Optional[DpmRunIdempotencyRecord]:
        with self._lock:
            record = self._idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None
