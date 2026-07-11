from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def trusted_test_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.getenv("LOTUS_ADVISE_TENANT_ID") is None:
        monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant-sg-001")
