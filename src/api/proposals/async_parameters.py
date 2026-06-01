from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path

ProposalAsyncCreateIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for proposal-create deduplication.",
        examples=["proposal-create-idem-async-001"],
    ),
]

ProposalAsyncCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional correlation id for asynchronous tracking. Generated when omitted.",
        examples=["corr-proposal-create-async-001"],
    ),
]

ProposalAsyncOperationIdPath = Annotated[
    str,
    Path(description="Asynchronous operation identifier.", examples=["pop_001"]),
]

ProposalAsyncCorrelationIdPath = Annotated[
    str,
    Path(
        description="Correlation id associated with asynchronous submission.",
        examples=["corr-proposal-create-async-001"],
    ),
]
