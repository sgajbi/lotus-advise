from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException

from src.api.routers.bank_demo_proof_responses import (
    RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX,
    RFC28_PROOF_VALIDATION_FAILED,
)
from src.api.sensitive_error_details import contains_sensitive_error_detail

_ProofOperationResult = TypeVar("_ProofOperationResult")


def run_bank_demo_proof_operation(
    operation: Callable[[], _ProofOperationResult],
) -> _ProofOperationResult:
    try:
        return operation()
    except ValueError as exc:
        raise bank_demo_proof_pack_exception(str(exc)) from exc


def bank_demo_proof_pack_exception(error_detail: str) -> HTTPException:
    return HTTPException(
        status_code=_proof_pack_error_status(error_detail),
        detail=_safe_proof_pack_error_detail(error_detail),
    )


def _proof_pack_error_status(error_detail: str) -> int:
    if error_detail.startswith(RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX):
        return 409
    return 422


def _safe_proof_pack_error_detail(error_detail: str) -> str:
    if not contains_sensitive_error_detail(error_detail):
        return error_detail
    if error_detail.startswith(RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX):
        return (
            f"{RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX}: "
            "material field review failed with sensitive detail redacted"
        )
    return f"{RFC28_PROOF_VALIDATION_FAILED}: source evidence failed validation"
