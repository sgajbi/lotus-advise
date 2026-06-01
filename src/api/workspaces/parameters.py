from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path

WorkspaceIdPath = Annotated[
    str,
    Path(description="Workspace session identifier.", examples=["aws_001"]),
]

WorkspaceVersionIdPath = Annotated[
    str,
    Path(description="Saved workspace version identifier.", examples=["awv_001"]),
]

WorkspaceCreateCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description=(
            "Optional trace and correlation identifier propagated through the advisory workflow."
        ),
        examples=["corr-workspace-1234"],
    ),
]

WorkspaceHandoffIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description=(
            "Required for the first workspace handoff to create a persisted proposal; optional "
            "for later version handoffs."
        ),
        examples=["workspace-handoff-idem-001"],
    ),
]

WorkspaceHandoffCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional correlation id captured in proposal lifecycle handoff audit.",
        examples=["corr-workspace-handoff-001"],
    ),
]
