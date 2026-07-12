from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Header, Path, Query

ProposalIdPath = Annotated[
    str,
    Path(description="Persisted proposal identifier.", examples=["pp_001"]),
]

ProposalVersionNoPath = Annotated[
    int,
    Path(description="Immutable proposal version number.", ge=1, examples=[1]),
]

ProposalNarrativeVersionNoPath = Annotated[
    int,
    Path(description="Immutable proposal version number containing the narrative.", ge=1),
]

ProposalCreateIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for proposal-create deduplication.",
        examples=["proposal-create-idem-001"],
    ),
]

ProposalCreateCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional correlation id captured in lifecycle audit reason payload.",
        examples=["corr-proposal-create-001"],
    ),
]

ProposalVersionCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-Id",
        description="Optional correlation id captured in version event reason payload.",
        examples=["corr-proposal-version-001"],
    ),
]

ProposalTransitionIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe transition writes.",
        examples=["proposal-transition-idem-001"],
    ),
]

ProposalApprovalIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe approval writes.",
        examples=["proposal-approval-idem-001"],
    ),
]

ProposalNarrativeReviewIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe narrative review writes.",
        examples=["proposal-narrative-review-idem-001"],
    ),
]

ProposalIncludeEvidenceQuery = Annotated[
    bool,
    Query(
        description="Include full evidence bundle in current version payload.",
        examples=[True],
    ),
]

ProposalVersionIncludeEvidenceQuery = Annotated[
    bool,
    Query(description="Include full evidence bundle in version payload.", examples=[True]),
]

ProposalPortfolioIdFilterQuery = Annotated[
    str | None,
    Query(description="Portfolio filter.", examples=["pf_01"]),
]

ProposalWorkflowStateFilterQuery = Annotated[
    str | None,
    Query(description="Current workflow state filter.", examples=["DRAFT"]),
]

ProposalCreatedByFilterQuery = Annotated[
    str | None,
    Query(description="Creator actor id filter.", examples=["advisor_123"]),
]

ProposalCreatedFromFilterQuery = Annotated[
    datetime | None,
    Query(
        description="Created-at lower bound in UTC ISO8601.",
        examples=["2026-02-19T00:00:00Z"],
    ),
]

ProposalCreatedToFilterQuery = Annotated[
    datetime | None,
    Query(
        description="Created-at upper bound in UTC ISO8601.",
        examples=["2026-02-20T00:00:00Z"],
    ),
]

ProposalListLimitQuery = Annotated[
    int,
    Query(description="Page size.", ge=1, le=100, examples=[20]),
]

ProposalListCursorQuery = Annotated[
    str | None,
    Query(description="Opaque cursor from previous list response.", examples=["pp_123"]),
]
