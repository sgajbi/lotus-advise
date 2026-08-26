from datetime import UTC, datetime

import pytest

from src.core.advisory.benchmark_assignment_evidence import BenchmarkAssignmentSourceEvidence
from src.integrations.lotus_core.benchmark_assignment import (
    LotusCoreBenchmarkAssignmentUnavailableError,
)
from src.runtime import advisory_provider_ports


def _source_evidence() -> BenchmarkAssignmentSourceEvidence:
    return BenchmarkAssignmentSourceEvidence(
        effective_benchmark_id="BM_GLOBAL_BALANCED",
        effective_as_of_date="2026-03-25",
        effective_from_date="2026-01-01",
        effective_to_date=None,
        assignment_source="benchmark_policy_engine",
        assignment_status="active",
        assignment_recorded_at=datetime(2026, 3, 25, 9, 15, tzinfo=UTC),
        assignment_version=3,
        assignment_policy_pack_id="policy_pb_v1",
        assignment_source_system="mandate-booking-system",
        assignment_contract_version="rfc_062_v1",
        source_product_name="BenchmarkAssignment",
        source_product_version="v1",
        source_tenant_id="tenant_sg",
        source_generated_at=datetime(2026, 3, 25, 9, 16, tzinfo=UTC),
        source_restatement_version="v1",
        source_reconciliation_status="RECONCILED",
        source_data_quality_status="COMPLETE",
        source_latest_evidence_at=datetime(2026, 3, 25, 9, 14, tzinfo=UTC),
        source_batch_fingerprint="batch_20260325_0001",
        source_snapshot_id="snapshot_554",
        source_content_hash="sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        source_references=("lotus-core://benchmark/PF_554/2026-03-25",),
        source_lineage={
            "source_owner": "lotus-core",
            "source_product": "BenchmarkAssignment",
        },
        source_evidence_current=True,
        source_freshness_status="CURRENT",
        source_policy_version="policy-v1",
        supportability="READY",
    )


def test_runtime_port_wraps_source_owned_core_evidence_with_exact_request_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    source_evidence = _source_evidence()

    def _fetch(**kwargs: object) -> BenchmarkAssignmentSourceEvidence:
        captured.update(kwargs)
        return source_evidence

    monkeypatch.setattr(
        advisory_provider_ports, "fetch_benchmark_assignment_with_lotus_core", _fetch
    )

    resolution = (
        advisory_provider_ports._resolve_benchmark_assignment_evidence_with_lotus_core_port(
            "PF_554",
            "2026-03-25",
            "USD",
            {"tenant_id": "tenant_sg"},
            "corr-554",
        )
    )

    assert resolution.source_evidence is source_evidence
    assert captured == {
        "portfolio_id": "PF_554",
        "as_of_date": "2026-03-25",
        "reporting_currency": "USD",
        "policy_context": {"tenant_id": "tenant_sg"},
        "correlation_id": "corr-554",
    }


def test_runtime_port_converts_typed_core_failure_to_unavailable_review_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(**_kwargs: object) -> BenchmarkAssignmentSourceEvidence:
        raise LotusCoreBenchmarkAssignmentUnavailableError("BENCHMARK_EVIDENCE_SOURCE_NOT_FOUND")

    monkeypatch.setattr(
        advisory_provider_ports,
        "fetch_benchmark_assignment_with_lotus_core",
        _unavailable,
    )

    resolution = (
        advisory_provider_ports._resolve_benchmark_assignment_evidence_with_lotus_core_port(
            "PF_554",
            "2026-03-25",
            None,
            None,
            "corr-554",
        )
    )

    assert resolution.source_evidence is None
    assert resolution.reason_code == "BENCHMARK_EVIDENCE_SOURCE_NOT_FOUND"
