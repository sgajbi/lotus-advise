from __future__ import annotations

import re
from typing import Literal

from src.core.bank_demo_proof.validation import contains_sensitive_rfc28_term

SupportedClaimClassification = Literal[
    "IMPLEMENTATION_BACKED",
    "BACKEND_BACKED_UI_PENDING",
    "DEGRADED_SUPPORTED",
    "PLANNED_RFC",
    "UNSUPPORTED",
]
SupportedClaimAudience = Literal[
    "DEVELOPER",
    "BUSINESS_USER",
    "OPERATIONS",
    "SALES",
    "PRE_SALES",
    "CLIENT_DEMO",
    "RFP_SECURITY",
]
SupportedClaimMaterial = Literal[
    "README",
    "WIKI",
    "SUPPORTED_FEATURES",
    "DEMO_SCRIPT",
    "SCREENSHOT",
    "PRODUCT_ONE_PAGER",
    "RFP_RESPONSE",
    "SECURITY_PACK",
    "ARCHITECTURE_DECK",
    "ROI_STORY",
    "OPERATOR_RUNBOOK",
]
ProofAssetType = Literal[
    "API_RESPONSE_SUMMARY",
    "LIVE_VALIDATION_SUMMARY",
    "WORKBENCH_SCREENSHOT",
    "REPORT_PACKAGE_SUMMARY",
    "ARCHIVE_REFERENCE",
    "AI_LINEAGE_SUMMARY",
    "GOVERNANCE_INTEGRATION_SUMMARY",
    "SECURITY_CHECK_SUMMARY",
    "COMMERCIAL_DOCUMENT",
    "LOCAL_RUNTIME_BUNDLE",
]
ProofAssetAccessClass = Literal[
    "COMMIT_SAFE_SUMMARY",
    "CUSTOMER_CONSUMABLE_SUMMARY",
    "RESTRICTED_CUSTOMER_EVIDENCE",
    "OPERATOR_ONLY_DIAGNOSTICS",
    "LOCAL_ONLY_RUNTIME_EVIDENCE",
    "SECRET_MATERIAL",
]
ProofRetentionClass = Literal[
    "COMMIT_SOURCE",
    "LOCAL_EVIDENCE_BUNDLE",
    "ADVISORY_REVIEW_RECORD",
    "AUDIT_EVIDENCE",
    "DO_NOT_RETAIN",
]
ClientReadyProofPosture = Literal[
    "CLIENT_READY_REVIEW_REQUIRED",
    "CLIENT_READY_PUBLICATION_BLOCKED",
]

SUPPORTED_CLAIM_CLASSIFICATIONS: tuple[str, ...] = (
    "IMPLEMENTATION_BACKED",
    "BACKEND_BACKED_UI_PENDING",
    "DEGRADED_SUPPORTED",
    "PLANNED_RFC",
    "UNSUPPORTED",
)
RFC28_CANONICAL_SCENARIO_ID = "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL"
RFC28_CANONICAL_PROOF_MARKER = "BANK_DEMO_PROOF_PACK_CREATED"
RFC28_CANONICAL_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
RFC28_IDENTIFIER_MAX_LENGTH = 160
RFC28_BUSINESS_TITLE_MAX_LENGTH = 160
RFC28_CLAIM_TEXT_MAX_LENGTH = 1000
RFC28_ARTIFACT_URI_MAX_LENGTH = 512
RFC28_CONTENT_HASH_MAX_LENGTH = 80
RFC28_MAX_PROOF_ASSETS = 32
RFC28_MAX_REPOSITORY_SHAS = 16
RFC28_MAX_REF_LIST_ITEMS = 64
RFC28_SHA256_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC28_COMMIT_ALLOWED_ACCESS_CLASSES = {
    "COMMIT_SAFE_SUMMARY",
    "CUSTOMER_CONSUMABLE_SUMMARY",
}


def normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def normalize_ref_list(
    value: list[str],
    *,
    field_name: str,
    max_item_length: int = RFC28_IDENTIFIER_MAX_LENGTH,
) -> list[str]:
    normalized: list[str] = []
    for item in value:
        normalized_item = normalize_required_text(
            str(item),
            error_code=f"{field_name} cannot contain blank entries",
        )
        if len(normalized_item) > max_item_length:
            raise ValueError(f"{field_name} entry is too long")
        if contains_sensitive_technical_term(normalized_item):
            raise ValueError(f"{field_name} cannot contain sensitive technical detail")
        normalized.append(normalized_item)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} entries must be unique")
    return normalized


def contains_sensitive_technical_term(value: str) -> bool:
    return contains_sensitive_rfc28_term(value)
