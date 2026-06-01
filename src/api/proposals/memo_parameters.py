from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path, Query

ProposalMemoSourceVersionNoPath = Annotated[
    int,
    Path(description="Immutable proposal version number used as memo source.", ge=1),
]

ProposalMemoCreateIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe memo creation.",
        examples=["proposal-memo-create-idem-001"],
    ),
]

ProposalMemoReviewIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description="Optional idempotency key for replay-safe memo review writes.",
        examples=["proposal-memo-review-idem-001"],
    ),
]

ProposalMemoReportPackageEventIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description="Optional idempotency key for replay-safe memo report-package events.",
        examples=["proposal-memo-report-package-idem-001"],
    ),
]

ProposalMemoReportPackageIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description="Optional idempotency key for replay-safe memo report-package requests.",
        examples=["proposal-memo-report-package-idem-001"],
    ),
]

ProposalMemoAiCommentaryIdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        description="Optional idempotency key for replay-safe memo AI commentary requests.",
        examples=["proposal-memo-ai-commentary-idem-001"],
    ),
]

ProposalMemoAudienceQuery = Annotated[
    str | None,
    Query(
        description="Optional memo audience filter such as `ADVISOR` or `COMPLIANCE`.",
        examples=["ADVISOR"],
    ),
]
