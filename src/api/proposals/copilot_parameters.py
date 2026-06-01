from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path, Query

_COPILOT_CORRELATION_ID_MAX_LENGTH = 128
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_IDEMPOTENCY_KEY_MAX_LENGTH = 128
_COPILOT_CURSOR_MAX_LENGTH = 512

AdvisoryCopilotCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-ID",
        description="Correlation id for the advisory copilot operation.",
        max_length=_COPILOT_CORRELATION_ID_MAX_LENGTH,
    ),
]

AdvisoryCopilotOptionalIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description="Optional replay-safe advisory copilot action key.",
        max_length=_COPILOT_IDEMPOTENCY_KEY_MAX_LENGTH,
    ),
]

AdvisoryCopilotReviewIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required replay-safe advisory copilot review idempotency key.",
        min_length=1,
        max_length=_COPILOT_IDEMPOTENCY_KEY_MAX_LENGTH,
    ),
]

AdvisoryCopilotEvidencePacketIdPath = Annotated[
    str,
    Path(
        description="Advisory copilot evidence-packet identifier.",
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisoryCopilotRunIdPath = Annotated[
    str,
    Path(
        description="Advisory copilot run identifier.",
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisoryCopilotProposalIdPath = Annotated[
    str,
    Path(
        description="Proposal identifier.",
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisoryCopilotProposalVersionIdPath = Annotated[
    str,
    Path(
        description="Proposal version identifier.",
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisoryCopilotRunLimitQuery = Annotated[
    int,
    Query(description="Bounded page size. Default is 25; maximum is 100.", ge=1, le=100),
]

AdvisoryCopilotRunCursorQuery = Annotated[
    str | None,
    Query(
        description="Opaque cursor from a previous copilot run page.",
        max_length=_COPILOT_CURSOR_MAX_LENGTH,
    ),
]
