from __future__ import annotations

from typing import cast

from src.core.common.idempotency import normalize_required_idempotency_key
from src.core.proposals.exceptions import ProposalValidationError


def require_proposal_idempotency_key(idempotency_key: str | None) -> str:
    try:
        return cast(str, normalize_required_idempotency_key(idempotency_key))
    except ValueError as exc:
        raise ProposalValidationError("IDEMPOTENCY_KEY_REQUIRED") from exc
