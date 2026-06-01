from datetime import datetime, timezone

from src.infrastructure.proposals import postgres as postgres_module
from src.infrastructure.proposals import postgres_mappers


def test_postgres_mapper_compatibility_aliases_match_extracted_module() -> None:
    assert postgres_module._json_dump is postgres_mappers.json_dump
    assert postgres_module._json_dump_list is postgres_mappers.json_dump_list
    assert postgres_module._json_load_list is postgres_mappers.json_load_list
    assert postgres_module._optional_datetime is postgres_mappers.optional_datetime
    assert postgres_module._optional_iso is postgres_mappers.optional_iso
    assert postgres_module._optional_json is postgres_mappers.optional_json
    assert postgres_module._optional_load_json is postgres_mappers.optional_load_json
    assert postgres_module._to_operation is postgres_mappers.to_operation
    assert postgres_module._to_proposal is postgres_mappers.to_proposal
    assert postgres_module._to_version is postgres_mappers.to_version
    assert postgres_module._to_memo is postgres_mappers.to_memo
    assert postgres_module._to_memo_event is postgres_mappers.to_memo_event
    assert postgres_module._to_event is postgres_mappers.to_event
    assert postgres_module._to_approval is postgres_mappers.to_approval


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
