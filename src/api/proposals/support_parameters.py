from __future__ import annotations

from typing import Annotated

from fastapi import Path

ProposalIdempotencyKeyPath = Annotated[
    str,
    Path(
        description="Proposal create idempotency key.",
        examples=["proposal-create-idem-001"],
    ),
]
