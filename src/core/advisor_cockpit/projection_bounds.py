from __future__ import annotations

import hashlib

COCKPIT_IDENTIFIER_MAX_LENGTH = 160
COCKPIT_SUMMARY_MAX_LENGTH = 512
REFERENCE_DIGEST_LENGTH = 12


def bounded_optional_reference(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return bounded_reference(normalized)


def bounded_reference(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= COCKPIT_IDENTIFIER_MAX_LENGTH:
        return normalized
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:REFERENCE_DIGEST_LENGTH]
    prefix_length = COCKPIT_IDENTIFIER_MAX_LENGTH - REFERENCE_DIGEST_LENGTH - 1
    return f"{normalized[:prefix_length].rstrip('_')}_{digest}"


def bounded_content_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) <= COCKPIT_IDENTIFIER_MAX_LENGTH:
        return normalized
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def bounded_summary(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= COCKPIT_SUMMARY_MAX_LENGTH:
        return normalized
    suffix = "..."
    return normalized[: COCKPIT_SUMMARY_MAX_LENGTH - len(suffix)].rstrip() + suffix
