"""#557: the boundary that refuses a proposal has to say which boundary it was.

Executing the canonical journey against attributable revisions reached
`POST /advisory/proposals/simulate` answering 422
`PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE`, and neither the response body nor
the container log said anything more. Four distinct conditions produce that one code:

  * the proposal-layer resolver was never configured,
  * the Core-integration resolver was never configured,
  * Core returned something that is not a dict,
  * Core returned a dict that failed validation.

The specific cause is computed, carried through two frames, and discarded at the
third. Diagnosing which one had fired required reading the source, because the runtime
did not carry the answer -- which is the definition of a fail-closed guard that is
also undiagnosable.

The public code stays exactly as it was: callers and the HTTP surface are contracted
to it, and widening it would trade one problem for a contract break. The cause travels
beside it instead.
"""

from __future__ import annotations

import logging

import pytest

from src.api.services.advisory_simulation_validation import resolve_simulation_input
from src.core.proposals.context_ports import ProposalStatefulContextResolutionUnavailableError
from src.core.proposals.context_resolution import ProposalContextResolutionError

PUBLIC_REASON = "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE"


def test_the_public_reason_code_is_unchanged_by_carrying_a_cause() -> None:
    """`str(exc)` is the contract, so the cause must not leak into it.

    Asserted directly rather than trusted, because the natural way to make a cause
    visible is to append it to the message -- which is a contract change wearing the
    costume of a diagnostic improvement.
    """

    error = ProposalContextResolutionError(
        PUBLIC_REASON, underlying_reason="LOTUS_CORE_STATEFUL_CONTEXT_INVALID"
    )

    assert str(error) == PUBLIC_REASON
    assert error.underlying_reason == "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"


def test_a_cause_is_optional_so_existing_raisers_are_unaffected() -> None:
    """Several call sites raise this with a message alone and must keep working."""

    error = ProposalContextResolutionError(PUBLIC_REASON)

    assert str(error) == PUBLIC_REASON
    assert error.underlying_reason is None


def test_the_frame_that_discards_the_cause_now_carries_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Asserted where the cause is attached, not where it is later read.

    The first version of this suite only drove `resolve_simulation_input` with an error
    that already carried a cause, so it proved the log reads an attribute and nothing
    about the frame that sets it. Two mechanism swaps confirmed the gap: removing
    `underlying_reason=` from `_resolve_stateful_input`, and folding the cause into the
    public message, both left every test green. This is the test that fails for each.
    """

    from src.core.proposals import context_resolution

    def _unavailable(_stateful_input: object) -> object:
        raise ProposalStatefulContextResolutionUnavailableError(
            "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"
        )

    monkeypatch.setattr(context_resolution, "resolve_proposal_stateful_context", _unavailable)

    with pytest.raises(ProposalContextResolutionError) as raised:
        context_resolution._resolve_stateful_input(object())  # type: ignore[arg-type]

    assert str(raised.value) == PUBLIC_REASON, "the cause leaked into the public code"
    assert raised.value.underlying_reason == "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"


def test_the_underlying_cause_reaches_an_operator_through_the_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The whole point: a refusal an operator can attribute.

    Driven through `resolve_simulation_input`, the function that actually converts the
    domain error into the HTTP one, rather than against the logger call -- a test of
    the log statement in isolation stays green if the boundary stops reaching it.
    """

    def _refuse(_request: object) -> object:
        raise ProposalContextResolutionError(
            PUBLIC_REASON, underlying_reason="LOTUS_CORE_STATEFUL_CONTEXT_INVALID"
        )

    monkeypatch.setattr(
        "src.api.services.advisory_simulation_validation.resolve_simulation_request",
        _refuse,
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(Exception) as raised:
            resolve_simulation_input(object())  # type: ignore[arg-type]

    assert PUBLIC_REASON in str(raised.value)

    refusals = [
        record
        for record in caplog.records
        if record.getMessage() == "proposal.context_resolution_refused"
    ]
    assert len(refusals) == 1, "the refusal was not recorded exactly once"
    assert refusals[0].underlying_reason == "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"
    assert refusals[0].public_reason == PUBLIC_REASON


def test_a_refusal_carrying_no_cause_is_not_logged_as_though_it_did(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """No cause is not the same as an empty cause.

    A log line asserting `underlying_reason: None` would read as though the cause had
    been established and found absent, which is worse than not logging: it makes an
    unknown look like a finding.
    """

    def _refuse(_request: object) -> object:
        raise ProposalContextResolutionError("PROPOSAL_CONTEXT_INVALID")

    monkeypatch.setattr(
        "src.api.services.advisory_simulation_validation.resolve_simulation_request",
        _refuse,
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(Exception):
            resolve_simulation_input(object())  # type: ignore[arg-type]

    assert not [
        record
        for record in caplog.records
        if record.getMessage() == "proposal.context_resolution_refused"
    ]
