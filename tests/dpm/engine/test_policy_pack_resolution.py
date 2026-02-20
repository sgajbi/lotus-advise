from decimal import Decimal

from src.core.dpm.policy_packs import (
    apply_policy_pack_to_engine_options,
    parse_policy_pack_catalog,
    resolve_effective_policy_pack,
    resolve_policy_pack_definition,
)
from src.core.models import EngineOptions


def test_policy_pack_resolution_disabled_ignores_all_ids():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=False,
        request_policy_pack_id="req_pack",
        tenant_default_policy_pack_id="tenant_pack",
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is False
    assert resolved.source == "DISABLED"
    assert resolved.selected_policy_pack_id is None


def test_policy_pack_resolution_request_precedence():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="req_pack",
        tenant_default_policy_pack_id="tenant_pack",
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is True
    assert resolved.source == "REQUEST"
    assert resolved.selected_policy_pack_id == "req_pack"


def test_policy_pack_resolution_tenant_precedence_when_request_missing():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id="tenant_pack",
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is True
    assert resolved.source == "TENANT_DEFAULT"
    assert resolved.selected_policy_pack_id == "tenant_pack"


def test_policy_pack_resolution_global_precedence_when_request_and_tenant_missing():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is True
    assert resolved.source == "GLOBAL_DEFAULT"
    assert resolved.selected_policy_pack_id == "global_pack"


def test_policy_pack_resolution_none_when_enabled_and_no_ids():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    assert resolved.enabled is True
    assert resolved.source == "NONE"
    assert resolved.selected_policy_pack_id is None


def test_policy_pack_resolution_trims_policy_pack_ids():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="  req_pack  ",
        tenant_default_policy_pack_id="   ",
        global_default_policy_pack_id=" global_pack ",
    )
    assert resolved.source == "REQUEST"
    assert resolved.selected_policy_pack_id == "req_pack"


def test_policy_pack_catalog_parse_and_resolve():
    catalog = parse_policy_pack_catalog(
        '{"dpm_standard_v1":{"version":"2","turnover_policy":{"max_turnover_pct":"0.05"}}}'
    )
    assert "dpm_standard_v1" in catalog
    definition = catalog["dpm_standard_v1"]
    assert definition.version == "2"
    assert definition.turnover_policy.max_turnover_pct == Decimal("0.05")

    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    assert selected is not None
    assert selected.policy_pack_id == "dpm_standard_v1"


def test_policy_pack_apply_turnover_override():
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))
    catalog = parse_policy_pack_catalog(
        '{"dpm_standard_v1":{"turnover_policy":{"max_turnover_pct":"0.01"}}}'
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.max_turnover_pct == Decimal("0.01")


def test_policy_pack_catalog_parse_invalid_json_and_shape():
    assert parse_policy_pack_catalog("{bad-json}") == {}
    assert parse_policy_pack_catalog("[]") == {}


def test_policy_pack_catalog_parse_skips_invalid_rows():
    catalog = parse_policy_pack_catalog(
        '{"bad_row":"x"," ":"x","invalid_turnover":{"turnover_policy":{"max_turnover_pct":"bad"}}}'
    )
    assert catalog == {}


def test_policy_pack_resolve_definition_missing_or_none():
    resolution_none = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    assert resolve_policy_pack_definition(resolution=resolution_none, catalog={}) is None

    resolution_missing = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="missing_pack",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    assert resolve_policy_pack_definition(resolution=resolution_missing, catalog={}) is None


def test_policy_pack_apply_no_override_returns_original():
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))
    catalog = parse_policy_pack_catalog('{"dpm_standard_v1":{"version":"1"}}')
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    assert selected is not None
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.max_turnover_pct == Decimal("0.15")
