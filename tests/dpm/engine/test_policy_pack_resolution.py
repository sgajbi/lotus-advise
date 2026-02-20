from src.core.dpm.policy_packs import resolve_effective_policy_pack


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
