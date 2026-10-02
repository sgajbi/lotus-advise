from __future__ import annotations

import os

import pytest

from src.core.advisory.provider_ports import (
    configure_advisory_benchmark_assignment_evidence_provider,
)


@pytest.fixture(autouse=True)
def trusted_test_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_advisory_benchmark_assignment_evidence_provider(None)
    if os.getenv("LOTUS_ADVISE_TENANT_ID") is None:
        monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant-sg-001")
