from typing import Any

import httpx
import pytest

from src.core.models import ProposalResult, ProposalSimulateRequest
from src.integrations.lotus_core.contracts import (
    ADVISORY_SIMULATION_CONTRACT_VERSION,
    ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER,
)
from src.integrations.lotus_core.simulation import (
    LotusCoreSimulationUnavailableError,
    simulate_with_lotus_core,
)


def _request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "pf_client",
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                "fx_rates": [],
            },
            "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
        }
    )


def _result_payload() -> dict[str, Any]:
    result = ProposalResult.model_validate(
        {
            "proposal_run_id": "pr_client_001",
            "correlation_id": "corr_client_001",
            "status": "READY",
            "before": {
                "total_value": {"amount": "1000", "currency": "USD"},
                "cash_balances": [],
                "positions": [],
                "allocation_by_asset_class": [],
                "allocation_by_instrument": [],
                "allocation": [],
                "allocation_by_attribute": {},
                "allocation_views": [
                    {
                        "dimension": "asset_class",
                        "total_value": {"amount": "1000", "currency": "USD"},
                        "buckets": [
                            {
                                "key": "CASH",
                                "weight": "1.0",
                                "value": {"amount": "1000", "currency": "USD"},
                                "position_count": 1,
                            }
                        ],
                    }
                ],
            },
            "intents": [],
            "after_simulated": {
                "total_value": {"amount": "1000", "currency": "USD"},
                "cash_balances": [],
                "positions": [],
                "allocation_by_asset_class": [],
                "allocation_by_instrument": [],
                "allocation": [],
                "allocation_by_attribute": {},
                "allocation_views": [
                    {
                        "dimension": "asset_class",
                        "total_value": {"amount": "1000", "currency": "USD"},
                        "buckets": [
                            {
                                "key": "CASH",
                                "weight": "1.0",
                                "value": {"amount": "1000", "currency": "USD"},
                                "position_count": 1,
                            }
                        ],
                    }
                ],
            },
            "reconciliation": {
                "before_total_value": {"amount": "1000", "currency": "USD"},
                "after_total_value": {"amount": "1000", "currency": "USD"},
                "delta": {"amount": "0", "currency": "USD"},
                "tolerance": {"amount": "1", "currency": "USD"},
                "status": "OK",
            },
            "rule_results": [],
            "diagnostics": {
                "warnings": [],
                "suppressed_intents": [],
                "dropped_intents": [],
                "group_constraint_events": [],
                "tax_budget_constraint_events": [],
                "cash_ladder": [],
                "cash_ladder_breaches": [],
                "missing_fx_pairs": [],
                "funding_plan": [],
                "insufficient_cash": [],
                "data_quality": {"price_missing": [], "fx_missing": [], "shelf_missing": []},
            },
            "explanation": {"summary": "READY"},
            "allocation_lens": {
                "contract_version": ADVISORY_SIMULATION_CONTRACT_VERSION,
                "calculator_version": "lotus-core.allocation-calculator.v1",
                "dimensions": [
                    "asset_class",
                    "currency",
                    "sector",
                    "country",
                    "region",
                    "product_type",
                    "rating",
                ],
                "source": "LOTUS_CORE",
            },
            "lineage": {
                "portfolio_snapshot_id": "pf_client",
                "market_data_snapshot_id": "md_1",
                "request_hash": "sha256:test-hash",
                "idempotency_key": "idem-1",
                "engine_version": "0.1.0",
                "simulation_contract_version": ADVISORY_SIMULATION_CONTRACT_VERSION,
            },
        }
    )
    return result.model_dump(mode="json")


class _FakeResponse:
    def __init__(
        self, *, status_code: int, payload: dict[str, Any], headers: dict[str, str]
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request(
                "POST", "http://lotus-core/integration/advisory/proposals/simulate-execution"
            )
            raise httpx.HTTPStatusError(
                "upstream error",
                request=request,
                response=httpx.Response(status_code=self.status_code, json=self._payload),
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.response


def test_simulate_with_lotus_core_sends_contract_header_and_validates_response(monkeypatch):
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=200,
            payload=_result_payload(),
            headers={
                ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION
            },
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    result = simulate_with_lotus_core(
        request=_request(),
        request_hash="sha256:test-hash",
        idempotency_key="idem-1",
        correlation_id="corr-1",
    )

    headers = fake_client.calls[0]["headers"]
    assert (
        headers[ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER] == ADVISORY_SIMULATION_CONTRACT_VERSION
    )
    assert result.lineage.simulation_contract_version == ADVISORY_SIMULATION_CONTRACT_VERSION
    assert result.allocation_lens.contract_version == ADVISORY_SIMULATION_CONTRACT_VERSION
    assert result.allocation_lens.source == "LOTUS_CORE"
    assert result.before.allocation_views[0].dimension == "asset_class"
    assert fake_client.calls[0]["url"] == (
        "http://lotus-core:8201/integration/advisory/proposals/simulate-execution"
    )


def test_simulate_with_lotus_core_rejects_response_header_contract_mismatch(monkeypatch):
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=200,
            payload=_result_payload(),
            headers={ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: "advisory-simulation.v0"},
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    with pytest.raises(
        LotusCoreSimulationUnavailableError, match="LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH"
    ):
        simulate_with_lotus_core(
            request=_request(),
            request_hash="sha256:test-hash",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )


def test_simulate_with_lotus_core_rejects_problem_details_contract_mismatch(monkeypatch):
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=412,
            payload={
                "type": "https://lotus-platform.dev/problems/canonical-simulation/contract-version-mismatch",
                "title": "Canonical Simulation Contract Error",
                "status": 412,
                "detail": (
                    "Unsupported canonical simulation contract version: "
                    "advisory-simulation.v0. Expected advisory-simulation.v1."
                ),
                "instance": "/integration/advisory/proposals/simulate-execution",
                "error_code": "CANONICAL_SIMULATION_CONTRACT_VERSION_MISMATCH",
                "contract_version": ADVISORY_SIMULATION_CONTRACT_VERSION,
                "correlation_id": "corr-upstream-1",
            },
            headers={
                ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION
            },
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="Unsupported canonical simulation contract version",
    ):
        simulate_with_lotus_core(
            request=_request(),
            request_hash="sha256:test-hash",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )


def test_simulate_with_lotus_core_rejects_lineage_contract_mismatch(monkeypatch):
    payload = _result_payload()
    payload["lineage"]["simulation_contract_version"] = "advisory-simulation.v0"
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=200,
            payload=payload,
            headers={
                ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION
            },
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="response lineage did not match the canonical contract version",
    ):
        simulate_with_lotus_core(
            request=_request(),
            request_hash="sha256:test-hash",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )


def test_simulate_with_lotus_core_rejects_allocation_lens_contract_mismatch(monkeypatch):
    payload = _result_payload()
    payload["allocation_lens"]["contract_version"] = "advisory-simulation.v0"
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=200,
            payload=payload,
            headers={
                ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION
            },
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="response allocation lens did not match the canonical contract version",
    ):
        simulate_with_lotus_core(
            request=_request(),
            request_hash="sha256:test-hash",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )


def test_simulate_with_lotus_core_preserves_upstream_problem_status(monkeypatch):
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=422,
            payload={
                "type": "https://lotus-platform.dev/problems/canonical-simulation/request-validation-failed",
                "title": "Canonical Simulation Request Validation Failed",
                "status": 422,
                "detail": "Request payload does not satisfy the canonical simulation contract.",
                "instance": "/integration/advisory/proposals/simulate-execution",
                "error_code": "CANONICAL_SIMULATION_REQUEST_VALIDATION_FAILED",
                "contract_version": ADVISORY_SIMULATION_CONTRACT_VERSION,
                "correlation_id": "corr-upstream-2",
            },
            headers={
                ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION
            },
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    with pytest.raises(LotusCoreSimulationUnavailableError) as exc_info:
        simulate_with_lotus_core(
            request=_request(),
            request_hash="sha256:test-hash",
            idempotency_key="idem-1",
            correlation_id="corr-1",
        )

    assert exc_info.value.status_code == 422
    assert (
        "Request payload does not satisfy the canonical simulation contract."
        in exc_info.value.detail
    )


def test_simulate_with_lotus_core_backfills_missing_suitability_classification(monkeypatch):
    payload = _result_payload()
    payload["suitability"] = {
        "summary": {
            "new_count": 1,
            "resolved_count": 0,
            "persistent_count": 0,
            "highest_severity_new": "HIGH",
        },
        "issues": [
            {
                "issue_id": "MISSING_CLASSIFICATION",
                "issue_key": "PRODUCT_COMPLEXITY|STRUCT_NOTE_1",
                "dimension": "PRODUCT",
                "severity": "HIGH",
                "status_change": "NEW",
                "summary": "Complex product evidence is incomplete.",
                "remediation": "Capture client product-complexity evidence before proceeding.",
                "approval_implication": "CLIENT_CONTEXT_REQUIRED",
                "details": {"instrument_id": "STRUCT_NOTE_1"},
                "evidence": {
                    "as_of": "md_test",
                    "snapshot_ids": {
                        "portfolio_snapshot_id": "pf_client",
                        "market_data_snapshot_id": "md_1",
                    },
                },
                "policy_pack_id": "global-private-banking-baseline",
                "policy_version": "enterprise-suitability-policy.2026-04",
            }
        ],
        "policy_pack_id": "global-private-banking-baseline",
        "policy_version": "enterprise-suitability-policy.2026-04",
        "recommended_gate": "COMPLIANCE_REVIEW",
    }
    fake_client = _FakeClient(
        _FakeResponse(
            status_code=200,
            payload=payload,
            headers={
                ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION
            },
        )
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.integrations.lotus_core.simulation.httpx.Client", lambda timeout: fake_client
    )

    result = simulate_with_lotus_core(
        request=_request(),
        request_hash="sha256:test-hash",
        idempotency_key="idem-1",
        correlation_id="corr-1",
    )

    assert result.suitability is not None
    assert result.suitability.issues[0].classification == "NEW"
