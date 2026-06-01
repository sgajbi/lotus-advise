from datetime import datetime, timezone
from typing import Any

from src.api.services.advisory_simulation_idempotency import (
    save_simulation_idempotency_result,
)
from src.core.proposals.models import ProposalSimulationIdempotencyRecord


class _CaptureSimulationIdempotencyRepository:
    def __init__(self) -> None:
        self.saved_record: ProposalSimulationIdempotencyRecord | None = None

    def save_simulation_idempotency(self, record: ProposalSimulationIdempotencyRecord) -> None:
        self.saved_record = record


class _SerializableProposalResult:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return self._payload


def test_save_simulation_idempotency_result_defaults_created_at_to_utc() -> None:
    repository = _CaptureSimulationIdempotencyRepository()

    save_simulation_idempotency_result(
        repository=repository,  # type: ignore[arg-type]
        idempotency_key="simulation-idem-001",
        request_hash="sha256:simulation",
        result=_SerializableProposalResult({"status": "READY"}),  # type: ignore[arg-type]
    )

    assert repository.saved_record is not None
    assert repository.saved_record.created_at.tzinfo == timezone.utc
    assert repository.saved_record.idempotency_key == "simulation-idem-001"
    assert repository.saved_record.request_hash == "sha256:simulation"
    assert repository.saved_record.response_json == {"status": "READY"}


def test_save_simulation_idempotency_result_preserves_explicit_created_at() -> None:
    repository = _CaptureSimulationIdempotencyRepository()
    created_at = datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc)

    save_simulation_idempotency_result(
        repository=repository,  # type: ignore[arg-type]
        idempotency_key="simulation-idem-002",
        request_hash="sha256:simulation-explicit",
        result=_SerializableProposalResult({"status": "BLOCKED"}),  # type: ignore[arg-type]
        created_at=created_at,
    )

    assert repository.saved_record is not None
    assert repository.saved_record.created_at == created_at
    assert repository.saved_record.response_json == {"status": "BLOCKED"}
