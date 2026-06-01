from __future__ import annotations

from typing import Annotated

from fastapi import Header

ProposalSimulationIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key used for dedupe and hash conflict detection.",
        examples=["proposal-idem-001"],
    ),
]

ProposalArtifactIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key used for dedupe and hash conflict detection.",
        examples=["proposal-artifact-idem-001"],
    ),
]

ProposalSimulationCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional trace/correlation identifier propagated to logs and response.",
        examples=["corr-proposal-1234"],
    ),
]

ProposalArtifactCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional trace/correlation identifier propagated to logs and response.",
        examples=["corr-proposal-artifact-1234"],
    ),
]
