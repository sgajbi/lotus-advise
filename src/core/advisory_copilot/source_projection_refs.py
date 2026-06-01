from __future__ import annotations

from src.core.advisory_copilot.reference_models import CopilotSourceRef
from src.core.advisory_copilot.source_projection_text import (
    bounded_content_hash,
    bounded_projection_reference,
)

SOURCE_REF_ID_MAX_LENGTH = 160


def projection_source_ref(
    *,
    source_type: str,
    source_id: str,
    content_hash: str | None,
    access_class: str,
) -> CopilotSourceRef:
    return CopilotSourceRef(
        source_system="lotus-advise",
        source_type=source_type,
        source_id=bounded_projection_reference(source_id, max_length=SOURCE_REF_ID_MAX_LENGTH),
        content_hash=bounded_content_hash(content_hash),
        access_class=access_class,  # type: ignore[arg-type]
    )
