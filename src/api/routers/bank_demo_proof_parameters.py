from __future__ import annotations

from typing import Annotated

from fastapi import Header

from src.api.routers.bank_demo_proof_request import RFC28_CORRELATION_ID_MAX_LENGTH

BankDemoProofCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-ID",
        title="X-Correlation-ID",
        description="Optional caller correlation id propagated into proof metadata.",
        max_length=RFC28_CORRELATION_ID_MAX_LENGTH,
    ),
]
