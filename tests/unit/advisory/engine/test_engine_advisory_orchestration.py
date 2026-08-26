from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from src.core.advisory import orchestration
from src.core.advisory.benchmark_assignment_evidence import (
    BenchmarkAssignmentEvidenceResolution,
    BenchmarkAssignmentSourceEvidence,
)
from src.core.advisory.provider_ports import (
    AdvisoryRiskEnrichmentUnavailableError as LotusRiskEnrichmentUnavailableError,
)
from src.core.advisory.provider_ports import (
    AdvisorySimulationUnavailableError as LotusCoreSimulationUnavailableError,
)
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import EngineOptions, ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    portfolio_snapshot,
    price,
    shelf_entry,
)


def _request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot=portfolio_snapshot(
            portfolio_id="pf_orchestration",
            base_currency="USD",
            positions=[],
            cash_balances=[cash("USD", "1000")],
        ),
        market_data_snapshot=market_data_snapshot(
            prices=[price("EQ_1", "100", "USD")],
            fx_rates=[],
        ),
        shelf_entries=[shelf_entry("EQ_1", status="APPROVED")],
        options=EngineOptions(enable_proposal_simulation=True),
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
    )


def _local_result(
    request: ProposalSimulateRequest,
    *,
    request_hash: str = "sha256:orch",
) -> ProposalResult:
    return run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        idempotency_key="orch-idem",
        correlation_id="corr-orch",
    )


def test_evaluate_advisory_proposal_records_authoritative_core_and_policy_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    policy_context: dict[str, object] = {"policy_pack_id": "SG_PRIVATE_BANKING_REFERENCE"}

    def _simulate_with_lotus_core(**kwargs: Any) -> ProposalResult:
        assert kwargs["policy_context"] == policy_context
        return _local_result(request, request_hash=kwargs["request_hash"])

    monkeypatch.setattr(orchestration, "simulate_with_lotus_core", _simulate_with_lotus_core)
    monkeypatch.setattr(
        orchestration,
        "build_lotus_risk_dependency_state",
        lambda: SimpleNamespace(
            configured=False,
            degraded_reason="LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
        ),
    )
    monkeypatch.setattr(
        orchestration,
        "enrich_with_lotus_risk",
        lambda **kwargs: (_ for _ in ()).throw(LotusRiskEnrichmentUnavailableError("unavailable")),
    )

    result = orchestration.evaluate_advisory_proposal(
        request=request,
        request_hash="sha256:orch-core",
        idempotency_key="  orch-idem  ",
        correlation_id="corr-orch",
        policy_context=policy_context,
    )

    authority = result.explanation["authority_resolution"]
    assert authority == {
        "simulation_authority": "lotus_core",
        "risk_authority": "unavailable",
        "degraded": True,
        "degraded_reasons": ["LOTUS_RISK_DEPENDENCY_UNAVAILABLE"],
    }
    assert result.explanation["advisory_policy_context"] == policy_context
    assert result.proposal_decision_summary is not None


def test_evaluate_advisory_proposal_maps_current_core_benchmark_evidence_without_simulating_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        orchestration,
        "simulate_with_lotus_core",
        lambda **kwargs: _local_result(request, request_hash=kwargs["request_hash"]),
    )
    monkeypatch.setattr(
        orchestration,
        "enrich_with_lotus_risk",
        lambda **kwargs: kwargs["proposal_result"],
    )
    monkeypatch.setattr(
        orchestration,
        "resolve_advisory_benchmark_assignment_evidence",
        lambda **kwargs: (
            captured.update(kwargs)
            or BenchmarkAssignmentEvidenceResolution(
                source_evidence=BenchmarkAssignmentSourceEvidence(
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
                    source_content_hash=(
                        "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    ),
                    source_references=("lotus-core://benchmark/pf_orchestration/2026-03-25",),
                    source_lineage={
                        "source_owner": "lotus-core",
                        "source_product": "BenchmarkAssignment",
                    },
                    source_evidence_current=True,
                    source_freshness_status="CURRENT",
                    source_policy_version="policy-v1",
                    supportability="READY",
                )
            )
        ),
    )

    result = orchestration.evaluate_advisory_proposal(
        request=request,
        request_hash="sha256:orch-benchmark",
        idempotency_key="orch-idem",
        correlation_id="corr-orch",
        requested_as_of_date="2026-03-25",
        requested_reporting_currency="USD",
        policy_context={"benchmark_id": "BM_REQUESTED", "mandate_id": "MANDATE_1"},
    )

    assert captured == {
        "portfolio_id": "pf_orchestration",
        "requested_as_of_date": "2026-03-25",
        "requested_reporting_currency": "USD",
        "policy_context": {"benchmark_id": "BM_REQUESTED", "mandate_id": "MANDATE_1"},
        "correlation_id": "corr-orch",
    }
    assert result.proposal_review_evidence.benchmark_assignment.effective_benchmark_id == (
        "BM_GLOBAL_BALANCED"
    )
    assert result.proposal_review_evidence.current_mandate_limits.supportability == "UNAVAILABLE"
    assert result.proposal_review_evidence.simulated_mandate_limits.supportability == "UNAVAILABLE"

    replayed = ProposalResult.model_validate(result.model_dump(mode="json"))
    assert replayed.proposal_review_evidence == result.proposal_review_evidence


def test_evaluate_advisory_proposal_records_invalid_risk_configuration_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()

    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "ftp://risk.invalid")
    monkeypatch.setattr(
        orchestration,
        "simulate_with_lotus_core",
        lambda **kwargs: _local_result(request, request_hash=kwargs["request_hash"]),
    )
    monkeypatch.setattr(
        orchestration,
        "enrich_with_lotus_risk",
        lambda **kwargs: (_ for _ in ()).throw(LotusRiskEnrichmentUnavailableError("unavailable")),
    )

    result = orchestration.evaluate_advisory_proposal(
        request=request,
        request_hash="sha256:orch-invalid-risk",
        idempotency_key="orch-idem",
        correlation_id="corr-orch",
    )

    authority = result.explanation["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_core"
    assert authority["risk_authority"] == "unavailable"
    assert authority["degraded"] is True
    assert authority["degraded_reasons"] == ["LOTUS_RISK_DEPENDENCY_UNAVAILABLE"]
    assert result.proposal_decision_summary is not None


def test_evaluate_advisory_proposal_records_controlled_local_fallback_and_risk_degradation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()

    monkeypatch.setenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "true")
    monkeypatch.setenv("ENVIRONMENT", "ci")
    monkeypatch.setattr(
        orchestration,
        "simulate_with_lotus_core",
        lambda **kwargs: (_ for _ in ()).throw(
            LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")
        ),
    )
    monkeypatch.setattr(
        orchestration,
        "build_lotus_risk_dependency_state",
        lambda: SimpleNamespace(configured=True, degraded_reason=None),
    )
    monkeypatch.setattr(
        orchestration,
        "enrich_with_lotus_risk",
        lambda **kwargs: (_ for _ in ()).throw(LotusRiskEnrichmentUnavailableError("unavailable")),
    )

    result = orchestration.evaluate_advisory_proposal(
        request=request,
        request_hash="sha256:orch-fallback",
        idempotency_key="orch-idem",
        correlation_id="corr-orch",
    )

    authority = result.explanation["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_advise_local_fallback"
    assert authority["risk_authority"] == "unavailable"
    assert authority["degraded"] is True
    assert authority["degraded_reasons"] == [
        "LOTUS_CORE_SIMULATION_UNAVAILABLE",
        "LOTUS_RISK_ENRICHMENT_UNAVAILABLE",
    ]
    assert result.allocation_lens.source == "LOTUS_ADVISE_LOCAL_FALLBACK"
    assert result.proposal_decision_summary is not None
