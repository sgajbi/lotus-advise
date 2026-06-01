from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path

PolicyPackIdPath = Annotated[
    str,
    Path(description="Policy pack identifier.", examples=["SG_PRIVATE_BANKING_REFERENCE"]),
]

PolicyPackVersionPath = Annotated[
    str,
    Path(description="Policy pack version.", examples=["2026.05"]),
]

PolicyPackValidationIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy-pack validation.",
        examples=["validate-sg-policy-pack-001"],
    ),
]

PolicyPackActivationIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy-pack activation.",
        examples=["activate-sg-policy-pack-001"],
    ),
]
