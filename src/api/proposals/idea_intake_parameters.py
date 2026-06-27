from __future__ import annotations

from typing import Annotated

from fastapi import Header

IdeaProposalIntakeCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional source-safe correlation id supplied by lotus-idea.",
        max_length=128,
        examples=["corr-idea-proposal-001"],
    ),
]
