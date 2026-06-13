from __future__ import annotations

from src.integrations.lotus_ai.output_safety import (
    map_bounded_string_list,
    map_review_required_sections,
)


def test_map_review_required_sections_trims_bounds_and_discards_invalid_items() -> None:
    sections = map_review_required_sections(
        [
            "not-a-section",
            {"section_key": " ", "title": "Missing key", "text": "Text"},
            {"section_key": "OVERSIZED", "title": "Title", "text": "x" * 13},
            {"section_key": "SUMMARY", "title": " Summary ", "text": " Advisor review. "},
            {"section_key": "SECOND", "title": "Second", "text": "Second text"},
        ],
        max_sections=1,
        max_text_length=12,
    )

    assert sections == (
        {
            "section_key": "SECOND",
            "title": "Second",
            "text": "Second text",
            "review_state": "REVIEW_REQUIRED",
        },
    )


def test_map_review_required_sections_fails_closed_for_non_list_payload() -> None:
    assert map_review_required_sections({"section_key": "SUMMARY"}) == ()


def test_map_bounded_string_list_trims_bounds_and_discards_invalid_items() -> None:
    guidance = map_bounded_string_list(
        [" Review evidence. ", "", "x" * 25, 7, "Check policy posture.", "Extra item"],
        max_items=2,
        max_item_length=24,
    )

    assert guidance == ("Review evidence.", "Check policy posture.")
