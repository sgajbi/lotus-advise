from __future__ import annotations

from typing import Annotated

from fastapi import Header

ProposalExecutionHandoffIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description="Optional idempotency key for replay-safe execution handoff writes.",
        examples=["proposal-execution-handoff-idem-001"],
    ),
]
