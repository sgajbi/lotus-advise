from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path, Query

PolicyEvaluationProposalIdPath = Annotated[
    str,
    Path(
        description="Proposal identifier evaluated by the policy record.",
        examples=["pp_001"],
    ),
]

PolicyEvaluationProposalVersionIdPath = Annotated[
    str,
    Path(
        description="Immutable proposal version identifier evaluated by the policy record.",
        examples=["ppv_001"],
    ),
]

PolicyEvaluationFinalizeIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy evaluation finalization.",
        examples=["policy-evaluation-finalize-001"],
    ),
]

PolicyEvaluationStatusQuery = Annotated[
    str | None,
    Query(
        description=(
            "Optional aggregate policy posture filter. Defaults to evaluations requiring review."
        ),
        examples=["PENDING_REVIEW"],
    ),
]

PolicyEvaluationPortfolioIdQuery = Annotated[
    str | None,
    Query(
        description=(
            "Optional portfolio identifier filter sourced from the finalized policy evaluation "
            "evidence bundle."
        ),
        examples=["PB_SG_GLOBAL_BAL_001"],
    ),
]

PolicyEvaluationIdPath = Annotated[
    str,
    Path(description="Policy evaluation record identifier.", examples=["pev_123abc"]),
]

PolicyEvaluationEventIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy evaluation event capture.",
        examples=["policy-evaluation-review-001"],
    ),
]

PolicyEvaluationSignOffDecisionIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy sign-off decisions.",
        examples=["policy-evaluation-sign-off-001"],
    ),
]

PolicyEvaluationReportPackageIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy report-package requests.",
        examples=["policy-evaluation-report-package-001"],
    ),
]

PolicyEvaluationAiEvidenceIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required idempotency key for replay-safe policy AI evidence requests.",
        examples=["policy-evaluation-ai-evidence-001"],
    ),
]
