from __future__ import annotations

from typing import Any

DEFAULT_AI_OUTPUT_SECTION_LIMIT = 8
DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH = 96
DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH = 160
DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH = 4000
DEFAULT_AI_REVIEW_GUIDANCE_LIMIT = 8
DEFAULT_AI_REVIEW_GUIDANCE_LENGTH = 1000


def map_review_required_sections(
    value: Any,
    *,
    max_sections: int = DEFAULT_AI_OUTPUT_SECTION_LIMIT,
    max_section_key_length: int = DEFAULT_AI_OUTPUT_SECTION_KEY_LENGTH,
    max_title_length: int = DEFAULT_AI_OUTPUT_SECTION_TITLE_LENGTH,
    max_text_length: int = DEFAULT_AI_OUTPUT_SECTION_TEXT_LENGTH,
) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        return ()

    sections: list[dict[str, str]] = []
    for item in value:
        if len(sections) >= max_sections:
            break
        if not isinstance(item, dict):
            continue

        section_key = _bounded_text(item.get("section_key"), max_length=max_section_key_length)
        title = _bounded_text(item.get("title"), max_length=max_title_length)
        text = _bounded_text(item.get("text"), max_length=max_text_length)
        if section_key is None or title is None or text is None:
            continue

        sections.append(
            {
                "section_key": section_key,
                "title": title,
                "text": text,
                "review_state": "REVIEW_REQUIRED",
            }
        )
    return tuple(sections)


def map_bounded_string_list(
    value: Any,
    *,
    max_items: int = DEFAULT_AI_REVIEW_GUIDANCE_LIMIT,
    max_item_length: int = DEFAULT_AI_REVIEW_GUIDANCE_LENGTH,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()

    items: list[str] = []
    for item in value:
        if len(items) >= max_items:
            break
        bounded = _bounded_text(item, max_length=max_item_length)
        if bounded is not None:
            items.append(bounded)
    return tuple(items)


def map_bounded_text(value: Any, *, max_length: int) -> str | None:
    return _bounded_text(value, max_length=max_length)


def _bounded_text(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > max_length:
        return None
    return stripped
