from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import src.api.services.advisory_simulation_validation as simulation_validation
from src.core.proposals.context import ProposalContextResolutionError
from src.core.proposals.simulation_gate import ProposalSimulationGateError


def test_normalize_simulation_idempotency_key_delegates_to_shared_normalizer(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        simulation_validation,
        "normalize_required_idempotency_key",
        lambda idempotency_key: idempotency_key.strip(),
    )

    assert (
        simulation_validation.normalize_simulation_idempotency_key("  simulation-idem  ")
        == "simulation-idem"
    )


def test_normalize_simulation_idempotency_key_translates_validation_errors(
    monkeypatch,
) -> None:
    def _raise_value_error(_idempotency_key: str) -> str:
        raise ValueError("IDEMPOTENCY_KEY_REQUIRED")

    monkeypatch.setattr(
        simulation_validation,
        "normalize_required_idempotency_key",
        _raise_value_error,
    )

    with pytest.raises(HTTPException) as exc_info:
        simulation_validation.normalize_simulation_idempotency_key(" ")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "IDEMPOTENCY_KEY_REQUIRED"


def test_validate_simulation_request_enabled_translates_gate_errors(monkeypatch) -> None:
    def _raise_gate_error(**_kwargs) -> None:
        raise ProposalSimulationGateError("PROPOSAL_SIMULATION_DISABLED")

    monkeypatch.setattr(
        simulation_validation,
        "validate_proposal_simulation_enabled",
        _raise_gate_error,
    )

    with pytest.raises(HTTPException) as exc_info:
        simulation_validation.validate_simulation_request_enabled(  # type: ignore[arg-type]
            SimpleNamespace()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "PROPOSAL_SIMULATION_DISABLED"


def test_resolve_simulation_input_translates_context_resolution_errors(monkeypatch) -> None:
    def _raise_context_error(_request) -> None:
        raise ProposalContextResolutionError("PROPOSAL_STATEFUL_INPUT_REQUIRED")

    monkeypatch.setattr(
        simulation_validation,
        "resolve_simulation_request",
        _raise_context_error,
    )

    with pytest.raises(HTTPException) as exc_info:
        simulation_validation.resolve_simulation_input(SimpleNamespace())  # type: ignore[arg-type]

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "PROPOSAL_STATEFUL_INPUT_REQUIRED"
