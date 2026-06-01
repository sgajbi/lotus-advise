from __future__ import annotations

import hashlib
from typing import Any

DEFAULT_CALLER_APP = "lotus-advise"
DEFAULT_TENANT_ID = "tenant-sg-001"
DEFAULT_PROMPT_TEMPLATE_VERSION = "advisory-copilot-prompt-template.v1"
DEFAULT_OUTPUT_SCHEMA_VERSION = "advisory-copilot-output-schema.v1"
DEFAULT_EVALUATION_PACK_REF = "advisory-copilot-eval-pack.v1"


def optional_lineage_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def stable_copilot_record_id(*, prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"
