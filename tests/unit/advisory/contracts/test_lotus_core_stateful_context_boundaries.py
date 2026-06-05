from pathlib import Path

from src.integrations.lotus_core import stateful_context_market_data as market_data
from src.integrations.lotus_core import stateful_context_payload_values as payload_values
from src.integrations.lotus_core import stateful_context_shelf_entries as shelf_entries
from src.integrations.lotus_core import stateful_context_translation as facade


def test_stateful_context_translation_facade_preserves_public_imports() -> None:
    assert facade.build_prices is market_data.build_prices
    assert facade.derive_fx_rates is market_data.derive_fx_rates
    assert facade.build_shelf_entries is shelf_entries.build_shelf_entries
    assert facade.shelf_attributes_from_payload is shelf_entries.shelf_attributes_from_payload
    assert facade.decimal_or_none is payload_values.decimal_or_none


def test_stateful_context_translation_delegates_market_and_shelf_boundaries() -> None:
    source_root = Path(__file__).resolve().parents[4] / "src" / "integrations" / "lotus_core"
    facade_source = (source_root / "stateful_context_translation.py").read_text(encoding="utf-8")
    market_source = (source_root / "stateful_context_market_data.py").read_text(encoding="utf-8")
    shelf_source = (source_root / "stateful_context_shelf_entries.py").read_text(encoding="utf-8")

    for function_name in ("build_prices", "derive_fx_rates", "build_shelf_entries"):
        assert f"def {function_name}" not in facade_source

    assert "def build_prices" in market_source
    assert "def derive_fx_rates" in market_source
    assert "def build_shelf_entries" in shelf_source
