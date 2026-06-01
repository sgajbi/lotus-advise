from datetime import datetime, timezone

from src.infrastructure.proposals import postgres_mappers


def test_postgres_mappers_use_canonical_json_serialization() -> None:
    assert postgres_mappers.json_dump({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert postgres_mappers.json_dump_list([{"b": 2, "a": 1}]) == '[{"a":1,"b":2}]'
    assert postgres_mappers.optional_json(None) is None
    assert postgres_mappers.optional_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_postgres_mappers_drop_invalid_list_json_items() -> None:
    assert postgres_mappers.json_load_list('{"not":"a-list"}') == []
    assert postgres_mappers.json_load_list('[{"valid":true}, "skip", 7, {"also": "valid"}]') == [
        {"valid": True},
        {"also": "valid"},
    ]


def test_postgres_mappers_parse_optional_datetime_values() -> None:
    value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert postgres_mappers.optional_iso(value) == value.isoformat()
    assert postgres_mappers.optional_iso(None) is None
    assert postgres_mappers.optional_datetime(value.isoformat()) == value
    assert postgres_mappers.optional_datetime(None) is None


def test_to_proposal_returns_none_for_missing_row() -> None:
    assert postgres_mappers.to_proposal(None) is None
