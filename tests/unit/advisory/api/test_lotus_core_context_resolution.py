from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from src.core.proposals.models import ProposalReportResponse
from src.core.workspace.models import WorkspaceStatefulInput
from src.integrations.lotus_core.context_resolution import (
    LotusCoreContextResolutionError,
    configure_lotus_core_advisory_context_resolver,
    get_lotus_core_advisory_context_resolver_for_tests,
    reset_lotus_core_advisory_context_resolver_for_tests,
    resolve_lotus_core_advisory_context,
)
from src.integrations.lotus_report import (
    configure_memo_report_package_requester_for_lotus_report,
    configure_policy_sign_off_report_package_requester_for_lotus_report,
    configure_proposal_report_requester_for_lotus_report,
    get_lotus_report_requesters_for_tests,
    request_proposal_report_with_lotus_report,
)
from tests.shared.stateful_context_builders import build_resolved_stateful_context


@pytest.fixture(autouse=True)
def preserve_runtime_ports() -> Iterator[None]:
    original_resolver = get_lotus_core_advisory_context_resolver_for_tests()
    original_report_requesters = get_lotus_report_requesters_for_tests()
    yield
    configure_lotus_core_advisory_context_resolver(original_resolver)
    configure_proposal_report_requester_for_lotus_report(original_report_requesters[0])
    configure_memo_report_package_requester_for_lotus_report(original_report_requesters[1])
    configure_policy_sign_off_report_package_requester_for_lotus_report(
        original_report_requesters[2]
    )


def _stateful_input() -> WorkspaceStatefulInput:
    return WorkspaceStatefulInput(
        portfolio_id="DEMO_ADV_USD_001",
        as_of="2026-03-27",
        mandate_id="mandate_growth_01",
    )


def test_integration_runtime_ports_no_longer_discover_api_module() -> None:
    for path in Path("src/integrations").rglob("*.py"):
        source = path.read_text()

        assert "sys.modules" not in source, path
        assert "src.api.main" not in source, path


def test_api_runtime_explicitly_registers_lotus_core_context_resolver() -> None:
    source = Path("src/api/main.py").read_text()

    assert "configure_lotus_core_advisory_context_resolver" in source
    assert "resolve_stateful_context_with_lotus_core" in source


def test_lotus_core_context_resolution_requires_explicit_resolver() -> None:
    reset_lotus_core_advisory_context_resolver_for_tests()

    with pytest.raises(LotusCoreContextResolutionError) as exc_info:
        resolve_lotus_core_advisory_context(_stateful_input())

    assert str(exc_info.value) == "LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE"


def test_lotus_core_context_resolution_uses_configured_runtime_port() -> None:
    configure_lotus_core_advisory_context_resolver(
        lambda stateful_input: build_resolved_stateful_context(
            stateful_input.portfolio_id,
            stateful_input.as_of,
            prices=[{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            shelf_entries=[{"instrument_id": "EQ_1", "status": "APPROVED"}],
        )
    )

    resolved = resolve_lotus_core_advisory_context(_stateful_input())

    assert resolved.simulate_request.portfolio_snapshot.portfolio_id == "DEMO_ADV_USD_001"
    assert resolved.resolved_context.portfolio_snapshot_id == "ps_DEMO_ADV_USD_001_2026-03-27"


def test_lotus_core_context_resolution_rejects_invalid_configured_payload() -> None:
    configure_lotus_core_advisory_context_resolver(lambda _stateful_input: {"unexpected": True})

    with pytest.raises(LotusCoreContextResolutionError) as exc_info:
        resolve_lotus_core_advisory_context(_stateful_input())

    assert str(exc_info.value) == "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"


def test_lotus_report_request_uses_configured_runtime_port() -> None:
    configure_proposal_report_requester_for_lotus_report(
        lambda **_: ProposalReportResponse.model_construct(
            proposal={},
            report_request_id="prr_test",
            report_type="CLIENT_PROPOSAL_SUMMARY",
            report_service="lotus-report",
            status="READY",
            generated_at="2026-03-27T00:00:00+00:00",
            report_reference_id="lotus_report_artifact_test",
            artifact_url=None,
            explanation={"source": "configured_port"},
        )
    )

    response = request_proposal_report_with_lotus_report(request={})

    assert response.report_request_id == "prr_test"
    assert response.explanation == {"source": "configured_port"}
