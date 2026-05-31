from __future__ import annotations

import pytest

from src.core.common.actors import normalize_optional_support_note, normalize_required_actor_id


def test_required_actor_id_is_trimmed_and_rejects_blank_values() -> None:
    assert normalize_required_actor_id("  advisor_sg_001  ", error_code="ACTOR_REQUIRED") == (
        "advisor_sg_001"
    )

    with pytest.raises(ValueError, match="ACTOR_REQUIRED"):
        normalize_required_actor_id("   ", error_code="ACTOR_REQUIRED")


def test_optional_support_note_is_whitespace_folded_and_blank_safe() -> None:
    assert normalize_optional_support_note("  Reviewed pending\npolicy action.  ") == (
        "Reviewed pending policy action."
    )
    assert normalize_optional_support_note("   ") is None
    assert normalize_optional_support_note(None) is None
