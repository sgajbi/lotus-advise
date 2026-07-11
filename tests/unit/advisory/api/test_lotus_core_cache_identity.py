from __future__ import annotations

import json
from dataclasses import replace

from src.core.workspace.input_models import WorkspaceStatefulInput
from src.integrations.lotus_core.stateful_context_cache_identity import (
    LotusCoreCacheIdentity,
    classification_taxonomy_cache_key,
    fx_lookup_cache_key,
    instrument_enrichment_cache_key,
    instrument_lookup_cache_key,
    price_lookup_cache_key,
    stateful_context_cache_key,
)


def test_stateful_context_cache_key_carries_safe_source_scope(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "UAT")
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant-sg-001")

    cache_key = stateful_context_cache_key(
        WorkspaceStatefulInput(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of="2026-03-27",
            household_id="HH_001",
            mandate_id="MANDATE_001",
            benchmark_id="BENCHMARK_001",
        ),
        query_base_url="https://user:secret@core-query.dev.lotus/api?token=hidden#frag",
        control_plane_base_url=(
            "https://user:secret@core-control.dev.lotus/control?token=hidden#frag"
        ),
    )

    payload = json.loads(cache_key)

    assert payload["query_base_url"] == "https://core-query.dev.lotus/api"
    assert payload["control_plane_base_url"] == "https://core-control.dev.lotus/control"
    assert payload["environment"] == "uat"
    assert payload["tenant_id"] == "tenant-sg-001"
    assert payload["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert payload["as_of"] == "2026-03-27"
    assert payload["mandate_id"] == "MANDATE_001"
    assert payload["benchmark_id"] == "BENCHMARK_001"
    assert "secret" not in cache_key
    assert "token=hidden" not in cache_key


def test_cache_identity_distinguishes_rfc0020_semantic_dimensions() -> None:
    base = LotusCoreCacheIdentity(
        cache_family="stateful-context",
        query_base_url="http://core-query.dev.lotus",
        control_plane_base_url="http://core-control.dev.lotus",
        environment="dev",
        tenant_id="tenant-a",
        contract_version="contract.v1",
        portfolio_id="PF_A",
        as_of="2026-03-27",
        reporting_currency="USD",
        household_id="HH_A",
        mandate_id="MANDATE_A",
        benchmark_id="BENCHMARK_A",
        look_through_mode="DIRECT",
        allocation_dimensions="asset_class",
        valuation_options="TRUST_SNAPSHOT",
        risk_options="standard",
    )
    variants = [
        replace(base, query_base_url="http://core-query.uat.lotus"),
        replace(base, control_plane_base_url="http://core-control.uat.lotus"),
        replace(base, environment="uat"),
        replace(base, tenant_id="tenant-b"),
        replace(base, contract_version="contract.v2"),
        replace(base, portfolio_id="PF_B"),
        replace(base, as_of="2026-03-28"),
        replace(base, reporting_currency="SGD"),
        replace(base, household_id="HH_B"),
        replace(base, mandate_id="MANDATE_B"),
        replace(base, benchmark_id="BENCHMARK_B"),
        replace(base, look_through_mode="LOOK_THROUGH"),
        replace(base, allocation_dimensions="sector"),
        replace(base, valuation_options="MARK_TO_MARKET"),
        replace(base, risk_options="tail-risk"),
    ]

    baseline_key = base.cache_key()

    assert all(variant.cache_key() != baseline_key for variant in variants)
    assert len({baseline_key, *(variant.cache_key() for variant in variants)}) == 16


def test_cache_family_builders_create_distinct_semantic_keys(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant-sg-001")

    keys = {
        instrument_enrichment_cache_key(
            control_plane_base_url="http://core-control.dev.lotus",
            security_id="SEC_A",
            portfolio_id="PF_A",
            as_of="2026-03-27",
        ),
        classification_taxonomy_cache_key(
            control_plane_base_url="http://core-control.dev.lotus",
            as_of="2026-03-27",
            taxonomy_scope="instrument",
        ),
        instrument_lookup_cache_key(
            query_base_url="http://core-query.dev.lotus",
            instrument_id="SEC_A",
            portfolio_id="PF_A",
            as_of="2026-03-27",
        ),
        price_lookup_cache_key(
            query_base_url="http://core-query.dev.lotus",
            instrument_id="SEC_A",
            portfolio_id="PF_A",
            as_of="2026-03-27",
        ),
        fx_lookup_cache_key(
            query_base_url="http://core-query.dev.lotus",
            from_currency="EUR",
            to_currency="USD",
            portfolio_id="PF_A",
            as_of="2026-03-27",
        ),
    }

    assert len(keys) == 5
