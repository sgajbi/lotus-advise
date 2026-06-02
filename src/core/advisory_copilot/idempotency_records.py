from __future__ import annotations

from datetime import datetime
from typing import cast

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.idempotency_record_limits import (
    COPILOT_IDEMPOTENCY_RECORD_HASH_MAX_LENGTH,
    COPILOT_IDEMPOTENCY_RECORD_IDENTIFIER_MAX_LENGTH,
)
from src.core.advisory_copilot.record_text import normalize_required_record_text
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH


class AdvisoryCopilotRunIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key for a copilot action request.",
        min_length=1,
        max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
    )
    request_hash: str = Field(
        description="Canonical request hash mapped to the idempotency key.",
        min_length=1,
        max_length=COPILOT_IDEMPOTENCY_RECORD_HASH_MAX_LENGTH,
    )
    run_id: str = Field(
        description="Copilot run identifier mapped to the idempotency key.",
        min_length=1,
        max_length=COPILOT_IDEMPOTENCY_RECORD_IDENTIFIER_MAX_LENGTH,
    )
    created_at: datetime = Field(description="UTC timestamp when the mapping was created.")

    @field_validator("idempotency_key", "request_hash", "run_id")
    @classmethod
    def _normalize_required_idempotency_text(cls, value: str) -> str:
        return cast(
            str,
            normalize_required_record_text(value, error_code="COPILOT_IDEMPOTENCY_RECORD_REQUIRED"),
        )
