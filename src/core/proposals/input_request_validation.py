from typing import Any

from src.core.proposals.contract_types import ProposalInputMode


def _validate_legacy_input(
    *,
    simulate_request: Any,
    stateless_input: Any,
    stateful_input: Any,
    legacy_message: str,
    legacy_stateful_message: str,
) -> None:
    if simulate_request is None or stateless_input is not None:
        raise ValueError(legacy_message)
    if stateful_input is not None:
        raise ValueError(legacy_stateful_message)


def _validate_stateless_input(
    *,
    simulate_request: Any,
    stateless_input: Any,
    stateful_input: Any,
    stateless_message: str,
) -> None:
    if stateless_input is None or simulate_request is not None or stateful_input is not None:
        raise ValueError(stateless_message)


def _validate_stateful_input(
    *,
    simulate_request: Any,
    stateless_input: Any,
    stateful_input: Any,
    stateful_message: str,
) -> None:
    if stateful_input is None or simulate_request is not None or stateless_input is not None:
        raise ValueError(stateful_message)


def validate_exclusive_input_contract(
    *,
    input_mode: ProposalInputMode | None,
    simulate_request: Any,
    stateless_input: Any,
    stateful_input: Any,
    legacy_message: str,
    legacy_stateful_message: str,
    stateless_message: str,
    stateful_message: str,
) -> None:
    if input_mode is None:
        _validate_legacy_input(
            simulate_request=simulate_request,
            stateless_input=stateless_input,
            stateful_input=stateful_input,
            legacy_message=legacy_message,
            legacy_stateful_message=legacy_stateful_message,
        )
        return

    if input_mode == "stateless":
        _validate_stateless_input(
            simulate_request=simulate_request,
            stateless_input=stateless_input,
            stateful_input=stateful_input,
            stateless_message=stateless_message,
        )
        return

    _validate_stateful_input(
        simulate_request=simulate_request,
        stateless_input=stateless_input,
        stateful_input=stateful_input,
        stateful_message=stateful_message,
    )
