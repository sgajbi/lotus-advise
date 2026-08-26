import pytest

from src.core.advisory import provider_ports
from src.core.advisory.benchmark_assignment_evidence import BenchmarkAssignmentEvidenceResolution


@pytest.fixture(autouse=True)
def _reset_benchmark_assignment_provider_ports() -> None:
    provider_ports.reset_advisory_provider_ports_for_tests()
    yield
    provider_ports.reset_advisory_provider_ports_for_tests()


def test_benchmark_assignment_port_requires_requested_as_of_without_calling_provider() -> None:
    def _must_not_be_called(*_args: object) -> BenchmarkAssignmentEvidenceResolution:
        raise AssertionError("A source provider must not receive an incomplete temporal request")

    provider_ports.configure_advisory_benchmark_assignment_evidence_provider(_must_not_be_called)

    resolution = provider_ports.resolve_advisory_benchmark_assignment_evidence(
        portfolio_id="PF_554",
        requested_as_of_date=None,
        requested_reporting_currency="USD",
        policy_context={"tenant_id": "tenant_sg"},
        correlation_id="corr-554",
    )

    assert resolution == BenchmarkAssignmentEvidenceResolution.unavailable(
        "BENCHMARK_EVIDENCE_REQUESTED_AS_OF_MISSING"
    )


def test_benchmark_assignment_port_requires_runtime_provider() -> None:
    resolution = provider_ports.resolve_advisory_benchmark_assignment_evidence(
        portfolio_id="PF_554",
        requested_as_of_date="2026-03-25",
        requested_reporting_currency=None,
        policy_context=None,
        correlation_id="corr-554",
    )

    assert resolution == BenchmarkAssignmentEvidenceResolution.unavailable(
        "BENCHMARK_EVIDENCE_SOURCE_UNAVAILABLE"
    )


def test_benchmark_assignment_port_preserves_the_complete_source_request_and_can_be_reset() -> None:
    captured: list[object] = []
    expected = BenchmarkAssignmentEvidenceResolution.unavailable(
        "BENCHMARK_EVIDENCE_SOURCE_NOT_FOUND"
    )

    def _provider(*args: object) -> BenchmarkAssignmentEvidenceResolution:
        captured.extend(args)
        return expected

    provider_ports.configure_advisory_benchmark_assignment_evidence_provider(_provider)
    assert (
        provider_ports.get_advisory_benchmark_assignment_evidence_provider_for_tests() is _provider
    )

    resolution = provider_ports.resolve_advisory_benchmark_assignment_evidence(
        portfolio_id="PF_554",
        requested_as_of_date="2026-03-25",
        requested_reporting_currency="USD",
        policy_context={"tenant_id": "tenant_sg"},
        correlation_id="corr-554",
    )

    assert resolution is expected
    assert captured == [
        "PF_554",
        "2026-03-25",
        "USD",
        {"tenant_id": "tenant_sg"},
        "corr-554",
    ]

    provider_ports.reset_advisory_provider_ports_for_tests()
    assert provider_ports.get_advisory_benchmark_assignment_evidence_provider_for_tests() is None
