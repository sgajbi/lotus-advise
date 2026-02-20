from datetime import datetime, timezone
from typing import Optional

from src.core.dpm_runs.models import (
    DpmRunIdempotencyLookupResponse,
    DpmRunIdempotencyRecord,
    DpmRunLookupResponse,
    DpmRunRecord,
)
from src.core.dpm_runs.repository import DpmRunRepository
from src.core.models import RebalanceResult


class DpmRunNotFoundError(Exception):
    pass


class DpmRunSupportService:
    def __init__(self, *, repository: DpmRunRepository) -> None:
        self._repository = repository

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
