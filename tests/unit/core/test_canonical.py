from src.core.common.canonical import canonical_json, hash_canonical_payload, strip_keys


def test_canonical_json_uses_stable_key_order_and_compact_separators() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_hash_canonical_payload_is_stable_for_equivalent_payloads() -> None:
    assert hash_canonical_payload({"b": 2, "a": 1}) == hash_canonical_payload({"a": 1, "b": 2})


def test_strip_keys_removes_excluded_keys_recursively_without_mutating_source() -> None:
    payload = {
        "portfolio_id": "pf_demo",
        "content_hash": "sha256:old",
        "nested": {
            "generated_at": "2026-06-19T00:00:00Z",
            "value": {"content_hash": "sha256:nested", "amount": "100.00"},
        },
        "items": [
            {"content_hash": "sha256:item", "name": "position"},
            {"generated_at": "2026-06-19T00:00:00Z", "name": "cash"},
        ],
    }

    stripped = strip_keys(payload, exclude={"content_hash", "generated_at"})

    assert stripped == {
        "portfolio_id": "pf_demo",
        "nested": {"value": {"amount": "100.00"}},
        "items": [{"name": "position"}, {"name": "cash"}],
    }
    assert payload["content_hash"] == "sha256:old"
    assert payload["nested"]["value"]["content_hash"] == "sha256:nested"
